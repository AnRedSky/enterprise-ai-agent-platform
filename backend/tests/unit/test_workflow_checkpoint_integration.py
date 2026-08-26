"""Workflow Execution 与 Checkpoint 集成单元测试。"""

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.models.workflow_execution import WorkflowNodeExecution
from app.services.workflow.execution import WorkflowExecutionService


@pytest.mark.asyncio
async def test_transition_node_completed_appends_checkpoint_in_same_transaction() -> None:
    """Node 从 running 完成时必须追加 Checkpoint，并在同一事务中提交状态与快照。"""
    execution = SimpleNamespace(
        id=uuid4(),
        worker_owner="worker:test",
        status="running",
        created_by=uuid4(),
        current_node_id="agent-1",
    )
    node = WorkflowNodeExecution(
        execution_id=execution.id,
        node_id="agent-1",
        status="running",
        attempt=2,
        input_data={"prompt": "hello"},
    )
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: node)),
        add=lambda _value: None,
        flush=AsyncMock(),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )
    service = WorkflowExecutionService(db)
    service.governance.trace = AsyncMock()
    service.checkpoint.append_next_in_transaction = AsyncMock(
        return_value=SimpleNamespace(sequence=0)
    )

    output = {"cursor": "next-node", "text": "ok"}
    updated = await service.transition_node(
        execution,
        "agent-1",
        "completed",
        output_data=output,
    )

    assert updated.status == "completed"
    service.checkpoint.append_next_in_transaction.assert_awaited_once()
    checkpoint_kwargs = service.checkpoint.append_next_in_transaction.await_args.kwargs
    assert checkpoint_kwargs["execution_id"] == execution.id
    assert checkpoint_kwargs["execution_status"] == "running"
    assert checkpoint_kwargs["node_id"] == "agent-1"
    assert checkpoint_kwargs["node_attempt"] == 2
    assert checkpoint_kwargs["node_status"] == "completed"
    assert checkpoint_kwargs["state_data"] == output
    assert checkpoint_kwargs["output_data"] == output
    assert checkpoint_kwargs["worker_owner"] == "worker:test"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_transition_node_non_terminal_does_not_append_checkpoint() -> None:
    """Node 进入 running 时不能提前创建完成态 Checkpoint。"""
    execution = SimpleNamespace(
        id=uuid4(),
        worker_owner="worker:test",
        status="running",
        created_by=uuid4(),
        current_node_id=None,
    )
    node = WorkflowNodeExecution(
        execution_id=execution.id,
        node_id="agent-1",
        status="pending",
        attempt=1,
    )
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: node)),
        add=lambda _value: None,
        flush=AsyncMock(),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )
    service = WorkflowExecutionService(db)
    service.governance.trace = AsyncMock()
    service.checkpoint.append_next_in_transaction = AsyncMock()

    await service.transition_node(execution, "agent-1", "running", input_data={"x": 1})

    service.checkpoint.append_next_in_transaction.assert_not_awaited()
    db.commit.assert_awaited_once()
