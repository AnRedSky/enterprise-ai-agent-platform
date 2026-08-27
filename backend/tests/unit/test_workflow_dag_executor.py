"""Workflow DAG Multi-frontier Branch Executor 单元测试。"""

from types import SimpleNamespace

import pytest

from app.services.workflow.checkpoint.recovery.dag_executor import WorkflowDagMultiFrontierExecutor


@pytest.mark.asyncio
async def test_multi_frontier_executes_each_branch_with_isolated_state_and_marks_join_ready() -> None:
    plan = SimpleNamespace(
        frontier_node_ids=("branch-a", "branch-b"),
        nodes=(
            {"id": "branch-a", "type": "input", "config": {}},
            {"id": "branch-b", "type": "input", "config": {}},
        ),
        state_data={"merged": True},
    )
    seen = []

    async def executor(node, state):
        seen.append((node["id"], dict(state)))
        state[node["id"]] = "completed"
        return state

    result = await WorkflowDagMultiFrontierExecutor.execute(
        plan,
        branch_state_data={"branch-a": {"a": 1}, "branch-b": {"b": 2}},
        executor=executor,
    )

    assert [item[0] for item in seen] == ["branch-a", "branch-b"]
    assert seen[0][1] == {"a": 1}
    assert seen[1][1] == {"b": 2}
    assert result.join_ready is True
    assert result.merged_state_data == {"a": 1, "b": 2, "branch-a": "completed", "branch-b": "completed"}


@pytest.mark.asyncio
async def test_multi_frontier_persists_each_branch_before_join() -> None:
    plan = SimpleNamespace(
        frontier_node_ids=("branch-a", "branch-b"),
        nodes=(
            {"id": "branch-a", "type": "input", "config": {}},
            {"id": "branch-b", "type": "input", "config": {}},
        ),
        state_data={},
    )
    checkpoints = []

    async def executor(node, state):
        state[node["id"]] = "completed"
        return state

    async def checkpoint_writer(node_id, state):
        checkpoints.append((node_id, dict(state)))

    result = await WorkflowDagMultiFrontierExecutor.execute(
        plan,
        branch_state_data={"branch-a": {}, "branch-b": {}},
        executor=executor,
        checkpoint_writer=checkpoint_writer,
    )

    assert checkpoints == [
        ("branch-a", {"branch-a": "completed"}),
        ("branch-b", {"branch-b": "completed"}),
    ]
    assert result.join_ready is True


@pytest.mark.asyncio
async def test_multi_frontier_checkpoint_failure_blocks_join_and_later_branch() -> None:
    plan = SimpleNamespace(
        frontier_node_ids=("branch-a", "branch-b"),
        nodes=(
            {"id": "branch-a", "type": "input", "config": {}},
            {"id": "branch-b", "type": "input", "config": {}},
        ),
        state_data={},
    )
    executed = []

    async def executor(node, state):
        executed.append(node["id"])
        return state

    async def checkpoint_writer(node_id, state):
        raise RuntimeError(f"checkpoint failed: {node_id}")

    with pytest.raises(RuntimeError, match="checkpoint failed: branch-a"):
        await WorkflowDagMultiFrontierExecutor.execute(
            plan,
            branch_state_data={"branch-a": {}, "branch-b": {}},
            executor=executor,
            checkpoint_writer=checkpoint_writer,
        )

    assert executed == ["branch-a"]


@pytest.mark.asyncio
async def test_multi_frontier_rejects_missing_branch_state() -> None:
    plan = SimpleNamespace(
        frontier_node_ids=("branch-a", "branch-b"),
        nodes=(
            {"id": "branch-a", "type": "input", "config": {}},
            {"id": "branch-b", "type": "input", "config": {}},
        ),
        state_data={},
    )

    async def executor(node, state):
        return state

    with pytest.raises(ValueError, match="缺少 Branch state"):
        await WorkflowDagMultiFrontierExecutor.execute(
            plan,
            branch_state_data={"branch-a": {"a": 1}},
            executor=executor,
        )


@pytest.mark.asyncio
async def test_multi_frontier_conflict_blocks_join() -> None:
    plan = SimpleNamespace(
        frontier_node_ids=("branch-a", "branch-b"),
        nodes=(
            {"id": "branch-a", "type": "input", "config": {}},
            {"id": "branch-b", "type": "input", "config": {}},
        ),
        state_data={},
    )

    async def executor(node, state):
        state["shared"] = node["id"]
        return state

    with pytest.raises(ValueError, match="冲突键"):
        await WorkflowDagMultiFrontierExecutor.execute(
            plan,
            branch_state_data={"branch-a": {}, "branch-b": {}},
            executor=executor,
        )


@pytest.mark.asyncio
async def test_branch_failure_does_not_reach_later_branch() -> None:
    plan = SimpleNamespace(
        frontier_node_ids=("branch-a", "branch-b"),
        nodes=(
            {"id": "branch-a", "type": "input", "config": {}},
            {"id": "branch-b", "type": "input", "config": {}},
        ),
        state_data={},
    )
    executed = []

    async def executor(node, state):
        executed.append(node["id"])
        if node["id"] == "branch-a":
            raise RuntimeError("branch failed")
        return state

    with pytest.raises(RuntimeError, match="branch failed"):
        await WorkflowDagMultiFrontierExecutor.execute(
            plan,
            branch_state_data={"branch-a": {}, "branch-b": {}},
            executor=executor,
        )

    assert executed == ["branch-a"]
