"""Real API + PostgreSQL Checkpoint 持久化验收。"""

import os
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
EXECUTION_ID = os.getenv("WORKFLOW_EXECUTION_ID")

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
    """真实 HTTP Execution 完成后，必须存在与 Node completion 同事务产生的 PostgreSQL Checkpoint。"""
    if not EXECUTION_ID:
        pytest.fail("WORKFLOW_EXECUTION_ID is required for checkpoint persistence validation")

    with _client() as client:
        execution = client.get(f"/workflows/executions/{EXECUTION_ID}")
        assert execution.status_code == 200, execution.text
        payload = execution.json()
    assert payload["status"] == "completed", payload

    async with SessionLocal() as db:
        result = await db.execute(
            select(WorkflowExecutionCheckpoint)
            .where(WorkflowExecutionCheckpoint.execution_id == UUID(EXECUTION_ID))
            .order_by(WorkflowExecutionCheckpoint.sequence.asc())
        )
        checkpoints = list(result.scalars().all())

    assert checkpoints, "真实 PostgreSQL 中未找到 Workflow Execution Checkpoint"
    assert [item.sequence for item in checkpoints] == list(range(len(checkpoints)))
    assert all(item.checkpoint_reason == "node.completed" for item in checkpoints)
    assert all(item.execution_id == UUID(EXECUTION_ID) for item in checkpoints)
    assert all(item.node_status == "completed" for item in checkpoints)
