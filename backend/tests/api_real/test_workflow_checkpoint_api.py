"""Real API + PostgreSQL Checkpoint 持久化验收。"""

import os
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from .execution_helpers import run_or_observe_execution

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")

pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20.0,
    )


@pytest.mark.asyncio
async def test_completed_execution_has_real_postgresql_checkpoint() -> None:
    """本轮新建的真实 HTTP Execution 完成后，必须存在 Node completion Checkpoint。"""
    if not WORKFLOW_ID:
        pytest.fail("WORKFLOW_ID is required for checkpoint persistence validation")

    with _client() as client:
        created = client.post(
            f"/workflows/{WORKFLOW_ID}/executions",
            json={"input_data": {"source": "checkpoint-persistence-real-gate"}},
        )
        assert created.status_code == 201, created.text
        execution_id = created.json()["id"]

        run_status, payload = run_or_observe_execution(
            client,
            execution_id,
            expected_http_status=200,
        )
        assert run_status in {200, 409}, run_status
        assert payload["status"] == "completed", payload

    async with SessionLocal() as db:
        result = await db.execute(
            select(WorkflowExecutionCheckpoint)
            .where(WorkflowExecutionCheckpoint.execution_id == UUID(execution_id))
            .order_by(WorkflowExecutionCheckpoint.sequence.asc())
        )
        checkpoints = list(result.scalars().all())

    assert checkpoints, f"真实 PostgreSQL 中未找到 Execution {execution_id} 的 Workflow Execution Checkpoint"
    assert [item.sequence for item in checkpoints] == list(range(len(checkpoints)))
    assert all(item.checkpoint_reason == "node.completed" for item in checkpoints)
    assert all(item.execution_id == UUID(execution_id) for item in checkpoints)
    assert all(item.node_status == "completed" for item in checkpoints)
