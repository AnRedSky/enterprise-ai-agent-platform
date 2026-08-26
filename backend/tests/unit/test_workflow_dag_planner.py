"""Workflow DAG Resume Frontier 规划器单元测试。

职责：验证多分支、汇聚、完成事实闭包与确定性 frontier 边界。
边界：只验证纯内存 Planner，不连接数据库、不调用 Worker 或 Runtime。
关键依赖：WorkflowDagResumePlanner。
"""

from __future__ import annotations

import pytest

from app.services.workflow.checkpoint.recovery import WorkflowDagResumePlanner


def _definition() -> dict:
    return {
        "nodes": [
            {"id": "input", "type": "input", "config": {}},
            {"id": "branch-a", "type": "agent", "config": {}},
            {"id": "branch-b", "type": "agent", "config": {}},
            {"id": "output", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "input", "target": "branch-a"},
            {"source": "input", "target": "branch-b"},
            {"source": "branch-a", "target": "output"},
            {"source": "branch-b", "target": "output"},
        ],
    }


def test_frontier_contains_all_ready_branches_in_definition_order() -> None:
    plan = WorkflowDagResumePlanner.plan(definition=_definition(), completed_node_ids={"input"})

    assert plan.completed_node_ids == ("input",)
    assert plan.frontier_node_ids == ("branch-a", "branch-b")


def test_merge_node_waits_until_all_predecessors_are_completed() -> None:
    definition = _definition()

    first = WorkflowDagResumePlanner.plan(
        definition=definition,
        completed_node_ids={"input", "branch-a"},
    )
    second = WorkflowDagResumePlanner.plan(
        definition=definition,
        completed_node_ids={"input", "branch-a", "branch-b"},
    )

    assert first.frontier_node_ids == ("branch-b",)
    assert second.frontier_node_ids == ("output",)


def test_completed_nodes_are_never_returned_in_frontier() -> None:
    plan = WorkflowDagResumePlanner.plan(
        definition=_definition(),
        completed_node_ids={"input", "branch-a", "branch-b", "output"},
    )

    assert plan.frontier_node_ids == ()


def test_planner_rejects_unknown_completed_node() -> None:
    with pytest.raises(ValueError, match="存在未知 completed Node"):
        WorkflowDagResumePlanner.plan(
            definition=_definition(),
            completed_node_ids={"input", "missing"},
        )


def test_planner_rejects_non_prefix_completed_nodes() -> None:
    with pytest.raises(ValueError, match="缺少已完成 predecessor"):
        WorkflowDagResumePlanner.plan(
            definition=_definition(),
            completed_node_ids={"input", "output"},
        )


def test_planner_rejects_non_set_completed_nodes() -> None:
    with pytest.raises(ValueError, match="completed_node_ids 必须为 set 或 frozenset"):
        WorkflowDagResumePlanner.plan(
            definition=_definition(),
            completed_node_ids=["input"],
        )


def test_planner_keeps_completed_node_output_deterministic() -> None:
    plan = WorkflowDagResumePlanner.plan(
        definition=_definition(),
        completed_node_ids={"branch-b", "input"},
    )

    assert plan.completed_node_ids == ("input", "branch-b")
    assert plan.frontier_node_ids == ("branch-a",)
