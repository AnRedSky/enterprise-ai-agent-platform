from __future__ import annotations

import json
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution
from app.services.workflow import WorkflowExecutionService

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")

pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20.0,
    )


def _require_context() -> None:
    if not ORGANIZATION_ID:
        pytest.fail("ORGANIZATION_ID is required for durable resume validation")


@contextmanager
def _resume_fixture_server():
    """提供一次失败、下一次成功的真实 OpenAI-compatible HTTP Provider。

    Args:
        无。

    Returns:
        一个可用于 Model Provider endpoint 的本地 HTTP URL。

    Raises:
        无；Provider 响应由测试内的计数器决定。

    副作用：启动测试进程内的临时 HTTP Provider；该服务不属于 API、Scheduler 或 Worker，测试结束后立即关闭。
    """
    calls = 0
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            nonlocal calls
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            with lock:
                calls += 1
                call_no = calls
            status = 503 if call_no == 1 else 200
            content = "resume source failure" if call_no == 1 else "resume completed"
            payload = {
                "id": f"resume-fixture-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "model": "resume-fixture-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
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
        yield f"http://127.0.0.1:{server.server_port}/v1", calls, lock
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


async def _wait_for_source_failure(execution_id: str, timeout_seconds: float = 20.0) -> WorkflowExecution:
    """等待真实 Worker 将 Source Execution 落到 failed 且释放 ownership。

    Args:
        execution_id: Source Execution ID。
        timeout_seconds: 最大等待秒数。

    Returns:
        已完成失败收敛的 Source Execution。

    Raises:
        AssertionError: 在期限内没有达到 `failed + no worker_owner`。
    """
    import asyncio
    from time import monotonic

    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        async with SessionLocal() as db:
            source = (
                await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
            ).scalar_one_or_none()
            if source is not None and source.status == "failed" and source.worker_owner is None:
                return source
        await asyncio.sleep(0.2)
    raise AssertionError(f"Source Execution did not settle to failed without ownership: {execution_id}")


async def _wait_for_execution_status(execution_id: str, expected: str, timeout_seconds: float = 30.0) -> WorkflowExecution:
    """等待 Resume Execution 通过真实 Worker 达到指定持久化终态。

    Args:
        execution_id: Resume Execution ID。
        expected: 期望的持久化状态。
        timeout_seconds: 最大等待秒数。

    Returns:
        达到目标状态的 WorkflowExecution。

    Raises:
        AssertionError: 超时仍未达到目标状态。
    """
    import asyncio
    from time import monotonic

    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        async with SessionLocal() as db:
            execution = (
                await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
            ).scalar_one_or_none()
            if execution is not None and execution.status == expected:
                return execution
        await asyncio.sleep(0.2)
    raise AssertionError(f"Execution did not reach {expected}: {execution_id}")


async def _create_resume_execution(source_id: str) -> WorkflowExecution:
    """通过正式 Domain Service 从真实 PostgreSQL 创建 Resume Execution。

    Args:
        source_id: failed Source Execution ID。

    Returns:
        新建的 pending Resume Execution。

    Raises:
        AssertionError: Source Execution 不存在。

    事务边界：Resume 创建由 `WorkflowExecutionService.resume_from_latest_checkpoint()` 完成，测试不直接写入 Resume 业务表。
    """
    async with SessionLocal() as db:
        source = (
            await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == source_id))
        ).scalar_one_or_none()
        if source is None:
            raise AssertionError(f"Source Execution not found: {source_id}")
        resume = await WorkflowExecutionService(db).resume_from_latest_checkpoint(source, source.created_by)
        return resume


def test_real_worker_executes_durable_resume_from_checkpoint():
    """验证 Source failed → Checkpoint → Resume pending → 独立 Worker → 后续 Node 成功的真实链路。"""
    _require_context()
    suffix = uuid.uuid4().hex[:10]
    provider_id = None
    profile_id = None

    with _resume_fixture_server() as fixture:
        endpoint, calls, lock = fixture
        try:
            with _client() as client:
                provider = client.post(
                    "/model-providers",
                    json={
                        "organization_id": ORGANIZATION_ID,
                        "name": f"durable-resume-provider-{suffix}",
                        "provider_type": "openai-compatible",
                        "provider_name": f"durable-resume-provider-{suffix}",
                        "endpoint": endpoint,
                        "credential_ref": f"DURABLE_RESUME_SECRET_{suffix}",
                    },
                )
                assert provider.status_code == 201, provider.text
                provider_id = provider.json()["id"]

                profile = client.post(
                    f"/model-providers/{provider_id}/profiles",
                    json={
                        "name": f"durable-resume-profile-{suffix}",
                        "model_type": "chat",
                        "model_name": "resume-fixture-model",
                        "is_default": True,
                    },
                )
                assert profile.status_code == 201, profile.text
                profile_id = profile.json()["id"]

                agent = client.post(
                    "/agents",
                    json={
                        "name": f"Durable Resume Agent {suffix}",
                        "description": "Real Worker durable resume acceptance fixture",
                        "system_prompt": "Return the provider result without modification.",
                        "model_id": f"durable-resume-model-{suffix}",
                        "model_profile_id": profile_id,
                    },
                )
                assert agent.status_code == 200, agent.text
                agent_id = agent.json()["id"]

                versions = client.get(f"/agents/{agent_id}/versions")
                assert versions.status_code == 200, versions.text
                published_agent = client.post(
                    f"/agents/{agent_id}/publish",
                    json={"version_id": versions.json()[0]["id"]},
                )
                assert published_agent.status_code == 200, published_agent.text

                workflow = client.post(
                    "/workflows",
                    json={
                        "name": f"Durable Resume {suffix}",
                        "description": "Source failure after first node, resume from PostgreSQL checkpoint",
                    },
                )
                assert workflow.status_code == 201, workflow.text
                workflow_id = workflow.json()["id"]

                version = client.post(
                    f"/workflows/{workflow_id}/versions",
                    json={
                        "definition": {
                            "config": {"timeout_ms": 5000, "retry_budget": {"max_retries": 0}},
                            "nodes": [
                                {"id": "prepare", "type": "input", "config": {}},
                                {
                                    "id": "provider-call",
                                    "type": "agent",
                                    "config": {
                                        "agent_id": agent_id,
                                        "prompt": "durable resume acceptance",
                                        "retry": {
                                            "max_attempts": 1,
                                            "backoff_ms": 0,
                                            "max_backoff_ms": 0,
                                            "jitter_ms": 0,
                                            "retryable_error_codes": ["HTTP_503"],
                                        },
                                    },
                                },
                            ],
                            "edges": [],
                        }
                    },
                )
                assert version.status_code == 201, version.text
                version_id = version.json()["id"]
                published_workflow = client.post(f"/workflows/{workflow_id}/versions/{version_id}/publish")
                assert published_workflow.status_code == 200, published_workflow.text

                execution = client.post(
                    f"/workflows/{workflow_id}/executions",
                    json={"input_data": {"source": "durable-resume-acceptance"}},
                )
                assert execution.status_code == 201, execution.text
                source_id = execution.json()["id"]
                run = client.post(f"/workflows/executions/{source_id}/run")
                assert run.status_code in (409, 503), run.text

            import asyncio
            source = asyncio.run(_wait_for_source_failure(source_id))
            assert source.status == "failed"

            async def verify_source_checkpoint() -> tuple[WorkflowExecutionCheckpoint, list[WorkflowNodeExecution]]:
                async with SessionLocal() as db:
                    checkpoint = (
                        await db.execute(
                            select(WorkflowExecutionCheckpoint)
                            .where(WorkflowExecutionCheckpoint.execution_id == source.id)
                            .order_by(WorkflowExecutionCheckpoint.sequence.asc())
                        )
                    ).scalars().all()
                    nodes = (
                        await db.execute(
                            select(WorkflowNodeExecution)
                            .where(WorkflowNodeExecution.execution_id == source.id)
                            .order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc())
                        )
                    ).scalars().all()
                    assert len(checkpoint) == 1
                    return checkpoint[0], list(nodes)

            source_checkpoint, source_nodes = asyncio.run(verify_source_checkpoint())
            assert source_checkpoint.sequence == 1
            assert source_checkpoint.node_id == "prepare"
            assert source_checkpoint.node_status == "completed"
            assert source_checkpoint.state_data == {"source": "durable-resume-acceptance"}
            assert [(node.node_id, node.status) for node in source_nodes] == [
                ("prepare", "completed"),
                ("provider-call", "failed"),
            ]

            resume = asyncio.run(_create_resume_execution(source_id))
            assert resume.status == "pending"
            assert resume.resume_of_execution_id == source.id
            assert resume.resume_checkpoint_sequence == 1
            assert resume.input_data == source_checkpoint.state_data

            resumed = asyncio.run(_wait_for_execution_status(str(resume.id), "completed"))
            assert resumed.status == "completed"

            async def verify_resume_result() -> tuple[list[WorkflowExecutionCheckpoint], list[WorkflowNodeExecution]]:
                async with SessionLocal() as db:
                    checkpoints = (
                        await db.execute(
                            select(WorkflowExecutionCheckpoint)
                            .where(WorkflowExecutionCheckpoint.execution_id == resume.id)
                            .order_by(WorkflowExecutionCheckpoint.sequence.asc())
                        )
                    ).scalars().all()
                    nodes = (
                        await db.execute(
                            select(WorkflowNodeExecution)
                            .where(WorkflowNodeExecution.execution_id == resume.id)
                            .order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc())
                        ).scalars().all()
                    )
                    return list(checkpoints), list(nodes)

            resume_checkpoints, resume_nodes = asyncio.run(verify_resume_result())
            assert len(resume_checkpoints) == 1
            assert resume_checkpoints[0].sequence == 1
            assert resume_checkpoints[0].node_id == "provider-call"
            assert resume_checkpoints[0].node_status == "completed"
            assert [(node.node_id, node.status) for node in resume_nodes] == [("provider-call", "completed")]

            with lock:
                assert calls == 2
        finally:
            if profile_id or provider_id:
                with _client() as cleanup:
                    if profile_id:
                        response = cleanup.delete(f"/model-providers/model-profiles/{profile_id}")
                        assert response.status_code == 204, response.text
                    if provider_id:
                        response = cleanup.delete(f"/model-providers/{provider_id}")
                        assert response.status_code == 204, response.text
