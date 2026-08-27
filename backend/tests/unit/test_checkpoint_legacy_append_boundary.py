from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


@pytest.mark.asyncio
async def test_append_rejects_frontier_completion_without_source_frontier():
    service = WorkflowExecutionCheckpointService(MagicMock())

    with pytest.raises(HTTPException) as exc_info:
        await service.append(
            execution_id=uuid4(),
            sequence=0,
            execution_status="running",
            state_data={},
            checkpoint_reason="frontier_completed",
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_append_locks_execution_and_rejects_sequence_drift():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    service = WorkflowExecutionCheckpointService(db)

    execution = MagicMock(status="running", tenant_id=uuid4(), worker_owner=None, worker_attempt=0, worker_lease_expires_at=None)
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    sequence_result = MagicMock()
    sequence_result.scalar_one.return_value = 3
    db.execute.side_effect = [execution_result, sequence_result]

    with pytest.raises(HTTPException) as exc_info:
        await service.append(
            execution_id=uuid4(),
            sequence=5,
            execution_status="running",
            state_data={},
            checkpoint_reason="node.completed",
            node_id="node-a",
        )

    assert exc_info.value.status_code == 409
    assert db.commit.await_count == 0
    assert db.add.call_count == 0
    first_query = db.execute.await_args_list[0].args[0]
    assert getattr(first_query, "_for_update_arg", None) is not None


@pytest.mark.asyncio
async def test_append_accepts_next_sequence_after_execution_lock():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    service = WorkflowExecutionCheckpointService(db)

    execution = MagicMock(status="running", tenant_id=uuid4(), worker_owner=None, worker_attempt=0, worker_lease_expires_at=None)
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    sequence_result = MagicMock()
    sequence_result.scalar_one.return_value = 2
    db.execute.side_effect = [execution_result, sequence_result]

    checkpoint = await service.append(
        execution_id=uuid4(),
        sequence=3,
        execution_status="running",
        state_data={"cursor": 3},
        checkpoint_reason="node.completed",
        node_id="node-a",
    )

    assert checkpoint.sequence == 3
    db.add.assert_called_once_with(checkpoint)
    db.commit.assert_awaited_once()
