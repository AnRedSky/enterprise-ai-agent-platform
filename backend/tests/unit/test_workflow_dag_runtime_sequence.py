"""Workflow DAG Resume Runtime 顺序规划单元测试。

职责：验证单 frontier DAG 可以稳定展开为顺序 Runtime Node 计划。
边界：只测试纯内存拓扑规划，不连接数据库、不启动 Worker、不调用 Provider。
关键依赖：WorkflowDagResumeRuntimeSequencePlanner。
"""

from __future__ import annotations

import math

import pytest

from app.services.workflow.checkpoint.recovery.dag_runtime_sequence import (
    WorkflowDagResumeRuntimeSequencePlanner,
)


def _chain_definition() -> dict:
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


def test_sequence_planner_expands_linear_dag_in_topological_order() -> None:
    plans = WorkflowDagResumeRuntimeSequencePlanner.plan(
        definition=_chain_definition(),
        completed_node_ids={"start"},
        state_data={"input": "resume"},
    )

    assert [plan.frontier_node_id for plan in plans] == ["agent", "finish"]
    assert [plan.node["id"] for plan in plans] == ["agent", "finish"]
    assert all(plan.state_data == {"input": "resume"} for plan in plans)


def test_sequence_planner_returns_empty_when_source_already_completed() -> None:
    plans = WorkflowDagResumeRuntimeSequencePlanner.plan(
        definition=_chain_definition(),
        completed_node_ids={"start", "agent", "finish"},
        state_data={"content": "done"},
    )

    assert plans == ()


def test_sequence_planner_rejects_branch_frontier() -> None:
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

    with pytest.raises(ValueError, match="多个 frontier"):
        WorkflowDagResumeRuntimeSequencePlanner.plan(
            definition=definition,
            completed_node_ids={"start"},
            state_data={},
        )


def test_sequence_planner_does_not_mutate_definition_or_state() -> None:
    definition = _chain_definition()
    state = {"nested": {"value": 1}}

    plans = WorkflowDagResumeRuntimeSequencePlanner.plan(
        definition=definition,
        completed_node_ids={"start"},
        state_data=state,
    )

    definition["nodes"][1]["config"]["agent_id"] = "changed"
    state["nested"]["value"] = 2

    assert plans[0].node["config"]["agent_id"] == "agent-1"
    assert plans[0].state_data == {"nested": {"value": 1}}


def test_sequence_planner_rejects_non_json_safe_condition_state() -> None:
    definition = {
        "nodes": [
            {"id": "start", "type": "input", "config": {}},
            {"id": "left", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "start", "target": "left", "condition": {"op": "eq", "path": "status", "value": "ready"}},
        ],
    }

    with pytest.raises(ValueError, match="JSON-safe"):
        WorkflowDagResumeRuntimeSequencePlanner.plan(
            definition=definition,
            completed_node_ids={"start"},
            state_data={},
            state_data_by_node={"start": {"score": math.nan}},
        )
