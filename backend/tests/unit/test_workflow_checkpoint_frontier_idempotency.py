"""Execution-level frontier completion Checkpoint 幂等边界单元测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


class _Result:
    def __init__(self, value=None, values=None): self.value = value; self.values = [] if values is None else values
    def scalar_one_or_none(self): return self.value
    def scalar_one(self): return self.value
    def scalars(self): return self
    def all(self): return list(self.values)


def _execution():
    return SimpleNamespace(id=uuid4(), tenant_id=uuid4(), status="running", worker_owner="worker-a", worker_attempt=7, worker_lease_expires_at=None)


@pytest.mark.asyncio
async def test_frontier_completed_checkpoint_reuses_same_boundary() -> None:
    db = MagicMock(); frontier_id = uuid4(); execution = _execution(); existing = SimpleNamespace(sequence=4, execution_status="running", state_data={"left":1,"right":2}, worker_owner="worker-a")
    db.execute = AsyncMock(side_effect=[_Result(value=execution), _Result(values=[existing])]); db.flush = AsyncMock()
    actual = await WorkflowExecutionCheckpointService(db).append_next_in_transaction(execution_id=execution.id, execution_status="running", state_data={"left":1,"right":2}, checkpoint_reason="frontier_completed", worker_owner="worker-a", tenant_id=execution.tenant_id, expected_worker_owner=None, expected_worker_attempt=None, frontier_id=frontier_id)
    assert actual is existing; db.add.assert_not_called(); db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_frontier_completed_checkpoint_rejects_different_state() -> None:
    db = MagicMock(); frontier_id = uuid4(); execution = _execution(); existing = SimpleNamespace(sequence=4, execution_status="running", state_data={"left":1}, worker_owner="worker-a")
    db.execute = AsyncMock(side_effect=[_Result(value=execution), _Result(values=[existing])]); db.add = MagicMock(); db.flush = AsyncMock()
    with pytest.raises(HTTPException, match="payload 与本次写入不一致"):
        await WorkflowExecutionCheckpointService(db).append_next_in_transaction(execution_id=execution.id, execution_status="running", state_data={"left":2}, checkpoint_reason="frontier_completed", worker_owner="worker-a", tenant_id=execution.tenant_id, expected_worker_owner=None, expected_worker_attempt=None, frontier_id=frontier_id)
    db.add.assert_not_called(); db.flush.assert_not_awaited()
