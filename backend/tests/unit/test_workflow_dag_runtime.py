"""Workflow DAG Resume Runtime 计划单元测试。

职责：验证 DAG frontier 到 Runtime 单节点计划的安全收敛。
边界：只验证纯内存规划，不连接数据库、不启动 Worker、不调用 Provider。
关键依赖：WorkflowDagResumeRuntimePlanner。
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
    assert plan.frontier_node_id == "agent"
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


def test_dag_runtime_plan_rejects_multiple_frontier_nodes() -> None:
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

    with pytest.raises(ValueError, match="多个分支需要先冻结状态合并 Contract"):
        WorkflowDagResumeRuntimePlanner.plan(
            definition=definition,
            completed_node_ids={"start"},
            state_data={},
        )


def test_dag_runtime_plan_rejects_non_object_state() -> None:
    with pytest.raises(ValueError, match="state_data 必须为对象"):
        WorkflowDagResumeRuntimePlanner.plan(
            definition=_definition(),
            completed_node_ids={"start"},
            state_data=[],
        )
