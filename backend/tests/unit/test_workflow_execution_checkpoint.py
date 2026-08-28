"""Workflow Execution Checkpoint 服务单元测试。"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.services.workflow.checkpoint import WorkflowExecutionCheckpointService


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


@pytest.mark.asyncio
async def test_append_persists_immutable_checkpoint() -> None:
    """追加 Checkpoint 时必须保存完整状态快照并提交事务。"""
    execution_id = uuid4()
    execution = SimpleNamespace(
        id=execution_id, tenant_id=uuid4(), status="running", worker_owner="worker:test",
        worker_attempt=2, worker_lease_expires_at=None,
    )
    db = SimpleNamespace(
        add=lambda value: setattr(db, "added", value), commit=AsyncMock(), refresh=AsyncMock(),
        execute=AsyncMock(side_effect=[_Result(execution), _Result(None)]),
    )
    service = WorkflowExecutionCheckpointService(db)

    checkpoint = await service.append(
        execution_id=execution_id, sequence=0, execution_status="running", node_id="agent-1",
        node_attempt=2, node_status="completed",
        state_data={"cursor": "agent-2", "messages": [{"role": "assistant", "content": "ok"}]},
        input_data={"prompt": "hello"}, output_data={"text": "ok"}, checkpoint_reason="node.completed",
        worker_owner="worker:test", tenant_id=execution.tenant_id,
    )

    assert checkpoint.execution_id == execution_id
    assert checkpoint.sequence == 0
    assert checkpoint.node_id == "agent-1"
    assert checkpoint.node_attempt == 2
    assert checkpoint.execution_status == "running"
    assert checkpoint.node_status == "completed"
    assert checkpoint.state_data["cursor"] == "agent-2"
    assert checkpoint.checkpoint_reason == "node.completed"
    assert checkpoint.worker_owner == "worker:test"
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(checkpoint)


@pytest.mark.asyncio
async def test_append_rejects_invalid_sequence_and_reason() -> None:
    """Checkpoint 序号与原因必须具备明确业务语义。"""
    db = SimpleNamespace(add=lambda _value: None, commit=AsyncMock(), refresh=AsyncMock())
    service = WorkflowExecutionCheckpointService(db)

    with pytest.raises(ValueError, match="sequence"):
        await service.append(execution_id=uuid4(), sequence=-1, execution_status="running", state_data={}, checkpoint_reason="test")

    with pytest.raises(ValueError, match="reason"):
        await service.append(execution_id=uuid4(), sequence=0, execution_status="running", state_data={}, checkpoint_reason="   ")


@pytest.mark.asyncio
async def test_latest_reads_highest_sequence() -> None:
    """读取最新 Checkpoint 时必须按 sequence 倒序选择最新快照。"""
    latest = SimpleNamespace(sequence=7)
    result = SimpleNamespace(scalar_one_or_none=lambda: latest)
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    service = WorkflowExecutionCheckpointService(db)

    value = await service.latest(uuid4())

    assert value is latest
    db.execute.assert_awaited_once()
