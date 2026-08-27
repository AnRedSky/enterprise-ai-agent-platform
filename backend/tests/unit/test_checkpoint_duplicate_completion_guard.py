"""Checkpoint service 的 duplicate completion fail-closed 单元测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


@pytest.mark.asyncio
async def test_frontier_completion_writer_rejects_duplicate_completion_facts() -> None:
    db = AsyncMock()
    service = WorkflowExecutionCheckpointService(db)
    execution = MagicMock()
    execution.id = uuid4()
    execution.tenant_id = uuid4()
    execution.status = "running"

    first = MagicMock()
    second = MagicMock()
    execution_lookup = MagicMock()
    execution_lookup.scalar_one_or_none.return_value = execution
    boundary_lookup = MagicMock()
    boundary_lookup.scalars.return_value.all.return_value = [first, second]
    db.execute.side_effect = [execution_lookup, boundary_lookup]

    with pytest.raises(Exception, match="多个 completion Checkpoint"):
        await service.append_next_in_transaction(
            execution_id=execution.id,
            execution_status="running",
            state_data={"done": True},
            checkpoint_reason="frontier_completed",
            worker_owner="worker-new",
            tenant_id=execution.tenant_id,
            frontier_id=uuid4(),
        )

    db.add.assert_not_called()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("existing_status", "existing_state", "requested_status", "requested_state", "message"),
    [
        ("running", {"done": True}, "completed", {"done": True}, "lifecycle"),
        ("running", {"done": True}, "running", {"done": False}, "payload"),
    ],
)
async def test_frontier_completion_writer_rejects_existing_fact_drift(
    existing_status: str,
    existing_state: dict,
    requested_status: str,
    requested_state: dict,
    message: str,
) -> None:
    db = AsyncMock()
    service = WorkflowExecutionCheckpointService(db)
    execution = MagicMock()
    execution.id = uuid4()
    execution.tenant_id = uuid4()
    execution.status = requested_status

    existing = MagicMock()
    existing.execution_status = existing_status
    existing.state_data = existing_state
    execution_lookup = MagicMock()
    execution_lookup.scalar_one_or_none.return_value = execution
    boundary_lookup = MagicMock()
    boundary_lookup.scalars.return_value.all.return_value = [existing]
    db.execute.side_effect = [execution_lookup, boundary_lookup]

    with pytest.raises(Exception, match=message):
        await service.append_next_in_transaction(
            execution_id=execution.id,
            execution_status=requested_status,
            state_data=requested_state,
            checkpoint_reason="frontier_completed",
            worker_owner="worker-new",
            tenant_id=execution.tenant_id,
            frontier_id=uuid4(),
        )

    db.add.assert_not_called()
    db.flush.assert_not_awaited()
