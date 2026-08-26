"""Durable Resume Failure-after-Resume Real API 验收测试。

职责：通过真实 HTTP、真实 PostgreSQL 与独立 Worker 验证 Resume 再次失败时的 lineage、终态、Checkpoint 与 ownership 边界。
边界：不启动、停止或重启 API、Scheduler、Worker；测试前置服务由开发者管理。
关键依赖：独立 API Service、独立 Worker、PostgreSQL 与正式 WorkflowExecutionService。
"""

from __future__ import annotations

import asyncio
import os
import uuid
from time import monotonic

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
        pytest.skip("ACCESS_TOKEN is required for real API validation; use scripts/test/api-real/05_run_durable_resume_real_tests.ps1")
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=20.0)


def _require_context() -> None:
    if not ORGANIZATION_ID:
        pytest.skip("ORGANIZATION_ID is required; use scripts/test/api-real/05_run_durable_resume_real_tests.ps1")


async def _wait_for_terminal(execution_id: str, expected: str, timeout_seconds: float = 30.0) -> WorkflowExecution:
    """等待真实 Worker 将 Execution 持久化到指定终态。"""
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


async def _resume(source_id: str) -> WorkflowExecution:
    """通过正式 WorkflowExecutionService 创建 Resume Execution。"""
    async with SessionLocal() as db:
        source = (
            await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == source_id))
        ).scalar_one_or_none()
        if source is None:
            raise AssertionError(f"Source Execution not found: {source_id}")
        return await WorkflowExecutionService(db).resume_from_latest_checkpoint(source, source.created_by)


@pytest.mark.asyncio
async def test_real_worker_resume_failure_preserves_lineage_and_source_terminal_state():
    """验证 Resume 再次失败时 source lineage、checkpoint 与终态边界不会被破坏。"""
    _require_context()
    suffix = uuid.uuid4().hex[:10]
    broken_agent_id = str(uuid.uuid4())

    with _client() as client:
        workflow = client.post(
            "/workflows",
            json={
                "name": f"Durable Resume Failure {suffix}",
                "description": "Real Worker resume failure-after-resume boundary acceptance",
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
                            "id": "broken-agent",
                            "type": "agent",
                            "config": {
                                "agent_id": broken_agent_id,
                                "prompt": "durable resume failure-after-resume acceptance",
                                "retry": {
                                    "max_attempts": 1,
                                    "backoff_ms": 0,
                                    "max_backoff_ms": 0,
                                    "jitter_ms": 0,
                                    "retryable_error_codes": [],
                                },
                            },
                        },
                    ],
                    "edges": [{"source": "prepare", "target": "broken-agent"}],
                }
            },
        )
        assert version.status_code == 201, version.text
        version_id = version.json()["id"]
        published = client.post(f"/workflows/{workflow_id}/versions/{version_id}/publish")
        assert published.status_code == 200, published.text

        execution = client.post(
            f"/workflows/{workflow_id}/executions",
            json={"input_data": {"source": "resume-failure-after-resume"}},
        )
        assert execution.status_code == 201, execution.text
        source_id = execution.json()["id"]

        run = client.post(f"/workflows/executions/{source_id}/run")
        assert run.status_code in (404, 409), run.text

    source = await _wait_for_terminal(source_id, "failed")
    assert source.worker_owner is None
    assert source.workflow_version_id == uuid.UUID(version_id)

    async with SessionLocal() as db:
        checkpoints = (
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

    assert len(checkpoints) == 1
    assert checkpoints[0].sequence == 0
    assert checkpoints[0].node_id == "prepare"
    assert checkpoints[0].node_status == "completed"
    assert [(node.node_id, node.status) for node in nodes] == [
        ("prepare", "completed"),
        ("broken-agent", "failed"),
    ]

    resume = await _resume(source_id)
    assert resume.status == "pending"
    assert resume.resume_of_execution_id == source.id
    assert resume.resume_checkpoint_sequence == checkpoints[0].sequence
    assert resume.workflow_version_id == source.workflow_version_id
    assert resume.input_data == checkpoints[0].state_data

    resumed = await _wait_for_terminal(str(resume.id), "failed")
    assert resumed.status == "failed"
    assert resumed.worker_owner is None
    assert resumed.resume_of_execution_id == source.id
    assert resumed.resume_checkpoint_sequence == 0
    assert resumed.workflow_version_id == source.workflow_version_id

    async with SessionLocal() as db:
        source_after = (
            await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == source.id))
        ).scalar_one()
        resume_checkpoints = (
            await db.execute(
                select(WorkflowExecutionCheckpoint)
                .where(WorkflowExecutionCheckpoint.execution_id == resume.id)
                .order_by(WorkflowExecutionCheckpoint.sequence.asc())
            )
        ).scalars().all()
        resume_nodes = (
            await db.execute(
                select(WorkflowNodeExecution)
                .where(WorkflowNodeExecution.execution_id == resume.id)
                .order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc())
            )
        ).scalars().all()

    assert source_after.status == "failed"
    assert source_after.resume_of_execution_id is None
    assert source_after.workflow_version_id == resume.workflow_version_id
    assert resume_checkpoints == []
    assert [(node.node_id, node.status) for node in resume_nodes] == [("broken-agent", "failed")]
