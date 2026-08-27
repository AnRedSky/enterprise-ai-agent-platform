"""Checkpoint Replay 幂等性的 Worker ownership 独立性测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


@pytest.mark.asyncio
async def test_frontier_completion_idempotency_does_not_depend_on_worker_owner() -> None:
    """同一 Durable completion fact 被新 Worker Replay 时，不得因历史 owner 不同而追加事实。"""
    db = AsyncMock()
    service = WorkflowExecutionCheckpointService(db)
    execution_id = uuid4()
    tenant_id = uuid4()

    execution = MagicMock()
    execution.id = execution_id
    execution.tenant_id = tenant_id
    execution.status = "running"

    existing = MagicMock()
    existing.execution_status = "running"
    existing.state_data = {"done": True}
    existing.worker_owner = "worker-old"

    execution_lookup = MagicMock()
    execution_lookup.scalar_one_or_none.return_value = execution
    boundary_lookup = MagicMock()
    boundary_lookup.scalar_one_or_none.return_value = existing
    db.execute.side_effect = [execution_lookup, boundary_lookup]

    result = await service.append_next_in_transaction(
        execution_id=execution_id,
        execution_status="running",
        state_data={"done": True},
        checkpoint_reason="frontier_completed",
        worker_owner="worker-new",
        tenant_id=tenant_id,
        frontier_id=uuid4(),
    )

    assert result is existing
    db.add.assert_not_called()
    db.flush.assert_not_awaited()

