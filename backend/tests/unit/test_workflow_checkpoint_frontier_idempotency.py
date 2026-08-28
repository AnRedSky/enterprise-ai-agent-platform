"""Execution-level frontier completion Checkpoint 幂等边界单元测试。

职责：验证同一事务内重复提交相同 `frontier_completed` durable boundary 时不会生成第二个 sequence。
边界：只 mock AsyncSession，不连接 PostgreSQL、不启动 Worker、不调用 Provider。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


class _Result:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = [] if values is None else values

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return list(self.values)


@pytest.mark.asyncio
async def test_frontier_completed_checkpoint_reuses_same_boundary() -> None:
    db = AsyncMock()
    frontier_id = uuid4()
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), worker_owner="worker-a", worker_attempt=7,
        worker_lease_expires_at=None,
    )
    existing = SimpleNamespace(
        sequence=4, execution_status="running", state_data={"left": 1, "right": 2}, worker_owner="worker-a",
    )
    execution_result = _Result(value=execution)
    boundary_result = _Result(values=[existing])
    db.execute = AsyncMock(side_effect=[execution_result, boundary_result])

    service = WorkflowExecutionCheckpointService(db)
    actual = await service.append_next_in_transaction(
        execution_id=execution.id,
        execution_status="running",
        state_data={"left": 1, "right": 2},
        checkpoint_reason="frontier_completed",
        worker_owner="worker-a",
        tenant_id=execution.tenant_id,
        expected_worker_owner=None,
        expected_worker_attempt=None,
        frontier_id=frontier_id,
    )

    assert actual is existing
    db.add.assert_not_called()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_frontier_completed_checkpoint_does_not_reuse_different_state() -> None:
    db = AsyncMock()
    frontier_id = uuid4()
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), worker_owner="worker-a", worker_attempt=7,
        worker_lease_expires_at=None,
    )
    existing = SimpleNamespace(
        sequence=4, execution_status="running", state_data={"left": 1}, worker_owner="worker-a",
    )
    execution_result = _Result(value=execution)
    boundary_result = _Result(values=[existing])
    sequence_result = _Result(value=4)
    db.execute = AsyncMock(side_effect=[execution_result, boundary_result, sequence_result])

    service = WorkflowExecutionCheckpointService(db)
    actual = await service.append_next_in_transaction(
        execution_id=execution.id,
        execution_status="running",
        state_data={"left": 2},
        checkpoint_reason="frontier_completed",
        worker_owner="worker-a",
        tenant_id=execution.tenant_id,
        expected_worker_owner=None,
        expected_worker_attempt=None,
        frontier_id=frontier_id,
    )

    assert actual.sequence == 5
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
