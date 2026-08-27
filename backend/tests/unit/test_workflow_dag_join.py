"""Workflow DAG Join Readiness Contract 单元测试。"""

import pytest

from app.services.workflow.checkpoint.recovery.dag_join import WorkflowDagJoinReadinessService


def _definition() -> dict:
    return {
        "nodes": [
            {"id": "root", "type": "input", "config": {}},
            {"id": "a", "type": "input", "config": {}},
            {"id": "b", "type": "input", "config": {}},
            {"id": "join", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "root", "target": "a"},
            {"source": "root", "target": "b"},
            {"source": "a", "target": "join"},
            {"source": "b", "target": "join"},
        ],
    }


def test_join_is_not_ready_until_all_predecessors_complete() -> None:
    result = WorkflowDagJoinReadinessService.evaluate(
        definition=_definition(),
        node_id="join",
        completed_node_ids={"root", "a"},
        node_outputs={"a": {"answer": "a"}},
    )

    assert result.ready is False
    assert result.predecessor_node_ids == ("a", "b")
    assert result.state_data is None


def test_join_merges_all_completed_predecessor_outputs() -> None:
    result = WorkflowDagJoinReadinessService.evaluate(
        definition=_definition(),
        node_id="join",
        completed_node_ids={"root", "a", "b"},
        node_outputs={"a": {"a": 1}, "b": {"b": 2}},
    )

    assert result.ready is True
    assert result.state_data == {"a": 1, "b": 2}


def test_join_rejects_conflicting_predecessor_state() -> None:
    with pytest.raises(ValueError, match="冲突键"):
        WorkflowDagJoinReadinessService.evaluate(
            definition=_definition(),
            node_id="join",
            completed_node_ids={"root", "a", "b"},
            node_outputs={"a": {"shared": "a"}, "b": {"shared": "b"}},
        )


def test_join_rejects_missing_predecessor_output() -> None:
    with pytest.raises(ValueError, match="缺少 predecessor output"):
        WorkflowDagJoinReadinessService.evaluate(
            definition=_definition(),
            node_id="join",
            completed_node_ids={"root", "a", "b"},
            node_outputs={"a": {"a": 1}},
        )
