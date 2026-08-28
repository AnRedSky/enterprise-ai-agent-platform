from __future__ import annotations

import json
import os
import threading
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution
from app.services.workflow.checkpoint.recovery.resume_contract import WorkflowExecutionResumeContractService

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")

pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    if not TOKEN:
        pytest.skip("ACCESS_TOKEN is required for real API validation; use scripts/test/api-real/05_run_durable_resume_real_tests.ps1")
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=20.0)


def _require_context() -> None:
    if not ORGANIZATION_ID:
        pytest.skip("ORGANIZATION_ID is required; use scripts/test/api-real/05_run_durable_resume_real_tests.ps1")


@contextmanager
def _resume_fixture_server():
    state = {"calls": 0}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            with lock:
                state["calls"] += 1
                call_no = state["calls"]
            status = 503 if call_no == 1 else 200
            content = "resume source failure" if call_no == 1 else "resume completed"
            payload = {
                "id": f"resume-fixture-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "model": "resume-fixture-model",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", state, lock
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


async def _wait_for_source_failure(execution_id: str, timeout_seconds: float = 20.0) -> WorkflowExecution:
    import asyncio
    from time import monotonic
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        async with SessionLocal() as db:
            source = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))).scalar_one_or_none()
            if source is not None and source.status == "failed" and source.worker_owner is None:
                return source
        await asyncio.sleep(0.2)
    raise AssertionError(f"Source Execution did not settle to failed without ownership: {execution_id}")


async def _wait_for_execution_status(execution_id: str, expected: str, timeout_seconds: float = 30.0) -> WorkflowExecution:
    import asyncio
    from time import monotonic
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        async with SessionLocal() as db:
            execution = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))).scalar_one_or_none()
            if execution is not None and execution.status == expected:
                return execution
        await asyncio.sleep(0.2)
    raise AssertionError(f"Execution did not reach {expected}: {execution_id}")


async def _create_resume_execution(source_id: str) -> WorkflowExecution:
    """通过正式 Resume Contract 创建 Resume，并在同一事务内完成 Durable Bootstrap。"""
    async with SessionLocal() as db:
        source = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == source_id))).scalar_one_or_none()
        if source is None:
            raise AssertionError(f"Source Execution not found: {source_id}")
        outcome = await WorkflowExecutionResumeContractService(db).resume_with_outcome(source, source.created_by)
        return outcome.execution


@pytest.mark.asyncio
async def test_real_worker_executes_durable_resume_from_checkpoint():
    """验证 Source failed → Checkpoint → Resume pending → 独立 Worker → 后续 Node 成功的真实链路。"""
    _require_context()
    suffix = uuid.uuid4().hex[:10]
    provider_id = None
    profile_id = None

    with _resume_fixture_server() as fixture:
        endpoint, state, lock = fixture
        try:
            with _client() as client:
                provider = client.post("/model-providers", json={
                    "organization_id": ORGANIZATION_ID,
                    "name": f"durable-resume-provider-{suffix}",
                    "provider_type": "openai-compatible",
                    "provider_name": f"durable-resume-provider-{suffix}",
                    "endpoint": endpoint,
                    "credential_ref": f"DURABLE_RESUME_SECRET_{suffix}",
                })
                assert provider.status_code == 201, provider.text
                provider_id = provider.json()["id"]
                profile = client.post(f"/model-providers/{provider_id}/profiles", json={
                    "name": f"durable-resume-profile-{suffix}", "model_type": "chat",
                    "model_name": "resume-fixture-model", "is_default": True,
                })
                assert profile.status_code == 201, profile.text
                profile_id = profile.json()["id"]
                agent = client.post("/agents", json={
                    "name": f"Durable Resume Agent {suffix}",
                    "description": "Real Worker durable resume acceptance fixture",
                    "system_prompt": "Return the provider result without modification.",
                    "model_id": f"durable-resume-model-{suffix}", "model_profile_id": profile_id,
                })
                assert agent.status_code == 200, agent.text
                agent_id = agent.json()["id"]
                versions = client.get(f"/agents/{agent_id}/versions")
                assert versions.status_code == 200, versions.text
                published_agent = client.post(f"/agents/{agent_id}/publish", json={"version_id": versions.json()[0]["id"]})
                assert published_agent.status_code == 200, published_agent.text
                workflow = client.post("/workflows", json={
                    "name": f"Durable Resume {suffix}",
                    "description": "Source failure after first node, resume from PostgreSQL checkpoint",
                })
                assert workflow.status_code == 201, workflow.text
                workflow_id = workflow.json()["id"]
                version = client.post(f"/workflows/{workflow_id}/versions", json={"definition": {
                    "config": {"timeout_ms": 5000, "retry_budget": {"max_retries": 0}},
                    "nodes": [
                        {"id": "prepare", "type": "input", "config": {}},
                        {"id": "provider-call", "type": "agent", "config": {
                            "agent_id": agent_id, "prompt": "durable resume acceptance",
                            "retry": {"max_attempts": 1, "backoff_ms": 0, "max_backoff_ms": 0, "jitter_ms": 0,
                                      "retryable_error_codes": ["HTTP_503"]},
                        }},
                    ],
                    "edges": [{"source": "prepare", "target": "provider-call"}],
                }})
                assert version.status_code == 201, version.text
                published_workflow = client.post(f"/workflows/{workflow_id}/versions/{version.json()['id']}/publish")
                assert published_workflow.status_code == 200, published_workflow.text
                execution = client.post(f"/workflows/{workflow_id}/executions", json={"input_data": {"source": "durable-resume-acceptance"}})
                assert execution.status_code == 201, execution.text
                source_id = execution.json()["id"]
                run = client.post(f"/workflows/executions/{source_id}/run")
                assert run.status_code in (409, 503), run.text

            source = await _wait_for_source_failure(source_id)
            assert source.status == "failed"

            async with SessionLocal() as db:
                checkpoints = (await db.execute(select(WorkflowExecutionCheckpoint).where(
                    WorkflowExecutionCheckpoint.execution_id == source.id
                ).order_by(WorkflowExecutionCheckpoint.sequence.asc()))).scalars().all()
                source_nodes = (await db.execute(select(WorkflowNodeExecution).where(
                    WorkflowNodeExecution.execution_id == source.id
                ).order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc()))).scalars().all()
            assert len(checkpoints) == 1
            source_checkpoint = checkpoints[0]
            assert source_checkpoint.sequence == 0
            assert source_checkpoint.node_id == "prepare"
            assert source_checkpoint.node_status == "completed"
            assert source_checkpoint.state_data == {"source": "durable-resume-acceptance"}
            assert [(node.node_id, node.status) for node in source_nodes] == [("prepare", "completed"), ("provider-call", "failed")]

            resume = await _create_resume_execution(source_id)
            assert resume.status == "pending"
            assert resume.resume_of_execution_id == source.id
            assert resume.resume_checkpoint_sequence == 0
            assert resume.input_data == source_checkpoint.state_data

            resumed = await _wait_for_execution_status(str(resume.id), "completed")
            assert resumed.status == "completed"

            async with SessionLocal() as db:
                resume_checkpoints = (await db.execute(select(WorkflowExecutionCheckpoint).where(
                    WorkflowExecutionCheckpoint.execution_id == resume.id
                ).order_by(WorkflowExecutionCheckpoint.sequence.asc()))).scalars().all()
                resume_nodes = (await db.execute(select(WorkflowNodeExecution).where(
                    WorkflowNodeExecution.execution_id == resume.id
                ).order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc()))).scalars().all()
            assert len(resume_checkpoints) == 1
            assert resume_checkpoints[0].sequence == 0
            assert resume_checkpoints[0].checkpoint_reason == "frontier_completed"
            assert resume_checkpoints[0].frontier_id is not None
            assert resume_checkpoints[0].node_id is None
            assert resume_checkpoints[0].node_status is None
            assert [(node.node_id, node.status) for node in resume_nodes] == [("prepare", "completed"), ("provider-call", "completed")]
            with lock:
                assert state["calls"] == 2
        finally:
            if profile_id or provider_id:
                with _client() as cleanup:
                    if profile_id:
                        response = cleanup.delete(f"/model-providers/model-profiles/{profile_id}")
                        assert response.status_code == 204, response.text
                    if provider_id:
                        response = cleanup.delete(f"/model-providers/{provider_id}")
                        assert response.status_code == 204, response.text
