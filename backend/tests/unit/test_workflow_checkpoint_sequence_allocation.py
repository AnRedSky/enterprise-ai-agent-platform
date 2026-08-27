"""Checkpoint 序号分配的单元测试。"""

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


@pytest.mark.asyncio
async def test_append_next_locks_execution_before_reading_sequence() -> None:
    """验证自动分配序号前先锁定 Execution，避免并发 Worker 计算相同序号。"""
    db = MagicMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    execution = MagicMock()
    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = execution
    second_result = MagicMock()
    second_result.scalar_one.return_value = 7
    db.execute.side_effect = [first_result, second_result]

    service = WorkflowExecutionCheckpointService(db)
    checkpoint = await service.append_next_in_transaction(
        execution_id=uuid4(),
        execution_status="running",
        state_data={"frontier": ["node-b"]},
        checkpoint_reason="node_completed",
        node_id="node-a",
        node_attempt=1,
        node_status="succeeded",
        output_data={"value": 1},
    )

    lock_statement = db.execute.await_args_list[0].args[0]
    assert "workflow_executions" in str(lock_statement)
    assert "FOR UPDATE" in str(lock_statement).upper()
    assert checkpoint.sequence == 8
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_append_next_rejects_unknown_execution() -> None:
    """验证不存在的 Execution 不允许产生孤立 Checkpoint。"""
    db = MagicMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    service = WorkflowExecutionCheckpointService(db)
    with pytest.raises(ValueError, match="Execution 不存在"):
        await service.append_next_in_transaction(
            execution_id=uuid4(),
            execution_status="running",
            state_data={},
            checkpoint_reason="node_completed",
        )

    db.add.assert_not_called()
    db.flush.assert_not_awaited()
