"""Workflow DAG Join Node 执行协调单元测试。"""

from copy import deepcopy

import pytest

from app.services.workflow.checkpoint.recovery.dag_join import WorkflowDagJoinReadiness
from app.services.workflow.checkpoint.recovery.dag_join_executor import WorkflowDagJoinExecutor


def _ready() -> WorkflowDagJoinReadiness:
    return WorkflowDagJoinReadiness(node_id="join", predecessor_node_ids=("a", "b"), ready=True, state_data={"a": 1, "b": 2})


@pytest.mark.asyncio
async def test_join_executor_persists_after_successful_execution() -> None:
    calls: list[dict] = []
    persisted: list[tuple[str, dict]] = []

    async def executor(state: dict) -> dict:
        calls.append(deepcopy(state))
        state["joined"] = True
        return state

    async def persister(node_id: str, state: dict) -> None:
        persisted.append((node_id, state))

    result = await WorkflowDagJoinExecutor.execute(_ready(), node={"id": "join"}, executor=executor, persister=persister)
    assert result.executed is True
    assert result.state_data == {"a": 1, "b": 2, "joined": True}
    assert calls == [{"a": 1, "b": 2}]
    assert persisted == [("join", {"a": 1, "b": 2, "joined": True})]


@pytest.mark.asyncio
async def test_join_executor_rejects_not_ready() -> None:
    readiness = WorkflowDagJoinReadiness("join", ("a", "b"), False, None)
    async def executor(state: dict) -> dict:
        return state
    with pytest.raises(ValueError, match="尚未 ready"):
        await WorkflowDagJoinExecutor.execute(readiness, node={"id": "join"}, executor=executor)


@pytest.mark.asyncio
async def test_join_executor_reuses_completed_fact_without_execution() -> None:
    calls = 0
    async def executor(state: dict) -> dict:
        nonlocal calls
        calls += 1
        return state
    result = await WorkflowDagJoinExecutor.execute(_ready(), node={"id": "join"}, executor=executor, already_completed=True)
    assert result.executed is False
    assert result.state_data == {"a": 1, "b": 2}
    assert calls == 0


@pytest.mark.asyncio
async def test_join_executor_rejects_node_identity_mismatch() -> None:
    async def executor(state: dict) -> dict:
        return state
    with pytest.raises(ValueError, match="node_id 不一致"):
        await WorkflowDagJoinExecutor.execute(_ready(), node={"id": "other"}, executor=executor)


@pytest.mark.asyncio
async def test_join_executor_rejects_non_object_output() -> None:
    async def executor(state: dict) -> dict:
        return "invalid"  # type: ignore[return-value]
    with pytest.raises(ValueError, match="执行结果必须为对象"):
        await WorkflowDagJoinExecutor.execute(_ready(), node={"id": "join"}, executor=executor)
