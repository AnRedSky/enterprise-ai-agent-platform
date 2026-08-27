"""Workflow DAG Resume Runtime 计划单元测试。

职责：验证 DAG frontier 到 Runtime 多 Node 计划的安全收敛。
边界：只验证纯内存规划，不连接数据库、不启动 Worker、不调用 Provider。
关键依赖：WorkflowDagResumeRuntimePlanner、WorkflowDagBranchStateMergeService。
"""

from __future__ import annotations

import pytest

from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlanner


def _definition() -> dict:
    return {
        "nodes": [
            {"id": "start", "type": "input", "config": {}},
            {"id": "agent", "type": "agent", "config": {"agent_id": "agent-1"}},
            {"id": "finish", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "start", "target": "agent"},
            {"source": "agent", "target": "finish"},
        ],
    }


def test_dag_runtime_plan_returns_single_frontier_node() -> None:
    plan = WorkflowDagResumeRuntimePlanner.plan(
        definition=_definition(),
        completed_node_ids={"start"},
        state_data={"input": "resume"},
    )

    assert plan.completed_node_ids == ("start",)
    assert plan.frontier_node_ids == ("agent",)
    assert plan.frontier_node_id == "agent"
    assert plan.nodes == ({"id": "agent", "type": "agent", "config": {"agent_id": "agent-1"}},)
    assert plan.node == {"id": "agent", "type": "agent", "config": {"agent_id": "agent-1"}}
    assert plan.state_data == {"input": "resume"}


def test_dag_runtime_plan_deep_copies_node_and_state() -> None:
    state = {"nested": {"value": 1}}
    definition = _definition()

    plan = WorkflowDagResumeRuntimePlanner.plan(
        definition=definition,
        completed_node_ids={"start"},
        state_data=state,
    )

    state["nested"]["value"] = 2
    definition["nodes"][1]["config"]["agent_id"] = "changed"

    assert plan.state_data == {"nested": {"value": 1}}
    assert plan.node["config"]["agent_id"] == "agent-1"


def test_dag_runtime_plan_supports_multiple_frontier_nodes_and_merges_branch_state() -> None:
    definition = {
        "nodes": [
            {"id": "start", "type": "input", "config": {}},
            {"id": "left", "type": "agent", "config": {"agent_id": "left-agent"}},
            {"id": "right", "type": "agent", "config": {"agent_id": "right-agent"}},
            {"id": "join", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "start", "target": "left"},
            {"source": "start", "target": "right"},
            {"source": "left", "target": "join"},
            {"source": "right", "target": "join"},
        ],
    }

    plan = WorkflowDagResumeRuntimePlanner.plan(
        definition=definition,
        completed_node_ids={"start"},
        branch_state_data={
            "right": {"right_result": 2, "shared": "same"},
            "left": {"left_result": 1, "shared": "same"},
        },
    )

    assert plan.completed_node_ids == ("start",)
    assert plan.frontier_node_ids == ("left", "right")
    assert [node["id"] for node in plan.nodes] == ["left", "right"]
    assert plan.state_data == {"left_result": 1, "right_result": 2, "shared": "same"}

    with pytest.raises(ValueError, match="不能隐式选择单一 frontier"):
        _ = plan.frontier_node_id

    with pytest.raises(ValueError, match="不能隐式选择单一 Node"):
        _ = plan.node


def test_dag_runtime_plan_rejects_multiple_frontier_without_branch_state() -> None:
    definition = {
        "nodes": [
            {"id": "start", "type": "input", "config": {}},
            {"id": "left", "type": "output", "config": {}},
            {"id": "right", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "start", "target": "left"},
            {"source": "start", "target": "right"},
        ],
    }

    with pytest.raises(ValueError, match="多 frontier 必须提供 branch_state_data"):
        WorkflowDagResumeRuntimePlanner.plan(
            definition=definition,
            completed_node_ids={"start"},
            state_data={},
        )


def test_dag_runtime_plan_rejects_branch_state_key_not_in_frontier() -> None:
    definition = {
        "nodes": [
            {"id": "start", "type": "input", "config": {}},
            {"id": "left", "type": "output", "config": {}},
            {"id": "right", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "start", "target": "left"},
            {"source": "start", "target": "right"},
        ],
    }

    with pytest.raises(ValueError, match="非 frontier 分支状态"):
        WorkflowDagResumeRuntimePlanner.plan(
            definition=definition,
            completed_node_ids={"start"},
            branch_state_data={"left": {}, "right": {}, "ghost": {}},
        )


def test_dag_runtime_plan_rejects_conflicting_branch_state() -> None:
    definition = {
        "nodes": [
            {"id": "start", "type": "input", "config": {}},
            {"id": "left", "type": "output", "config": {}},
            {"id": "right", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "start", "target": "left"},
            {"source": "start", "target": "right"},
        ],
    }

    with pytest.raises(ValueError, match="冲突键"):
        WorkflowDagResumeRuntimePlanner.plan(
            definition=definition,
            completed_node_ids={"start"},
            branch_state_data={"left": {"shared": 1}, "right": {"shared": 2}},
        )


def test_dag_runtime_plan_rejects_non_object_state() -> None:
    with pytest.raises(ValueError, match="state_data 必须为对象"):
        WorkflowDagResumeRuntimePlanner.plan(
            definition=_definition(),
            completed_node_ids={"start"},
            state_data=[],
        )
