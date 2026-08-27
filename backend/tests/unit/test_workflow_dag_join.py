"""DAG Join Readiness 单元测试。"""

import pytest

from app.services.workflow.checkpoint.recovery.dag_join import WorkflowDagJoinReadinessService


@pytest.fixture
def conditional_definition() -> dict:
    """构造带条件入边的 Join DAG，验证 Join 只能消费 Planner 选定 predecessor。"""
    return {
        "nodes": [
            {"id": "a", "type": "task"},
            {"id": "b", "type": "task"},
            {"id": "join", "type": "task"},
        ],
        "edges": [
            {"source": "a", "target": "join", "condition": {"eq": [{"var": "route"}, "a"]}},
            {"source": "b", "target": "join", "default": True},
        ],
    }


def test_conditional_join_requires_planner_predecessors(conditional_definition: dict) -> None:
    """条件入边存在时，不能回退为消费 Definition 全部 predecessor。"""
    with pytest.raises(ValueError, match="必须由 Planner 提供"):
        WorkflowDagJoinReadinessService.evaluate(
            definition=conditional_definition,
            node_id="join",
            completed_node_ids={"a", "b"},
            node_outputs={"a": {"route": "a"}, "b": {"route": "b"}},
        )


def test_selected_predecessor_must_be_direct_and_unique(conditional_definition: dict) -> None:
    """Planner 快照中的 predecessor 必须来自当前 Join 的直接入边且不能重复。"""
    with pytest.raises(ValueError, match="不是 Join Node 的直接 predecessor"):
        WorkflowDagJoinReadinessService.evaluate(
            definition=conditional_definition,
            node_id="join",
            completed_node_ids={"a", "b"},
            node_outputs={"a": {"route": "a"}, "b": {"route": "b"}},
            predecessor_node_ids=("unknown",),
        )

    with pytest.raises(ValueError, match="不能重复"):
        WorkflowDagJoinReadinessService.evaluate(
            definition=conditional_definition,
            node_id="join",
            completed_node_ids={"a", "b"},
            node_outputs={"a": {"route": "a"}, "b": {"route": "b"}},
            predecessor_node_ids=("a", "a"),
        )


def test_selected_predecessor_join_is_ready(conditional_definition: dict) -> None:
    """Join 只消费 Planner 已选定且已完成的 predecessor。"""
    result = WorkflowDagJoinReadinessService.evaluate(
        definition=conditional_definition,
        node_id="join",
        completed_node_ids={"a"},
        node_outputs={"a": {"route": "a"}},
        predecessor_node_ids=("a",),
    )

    assert result.ready is True
    assert result.predecessor_node_ids == ("a",)
    assert result.state_data == {"route": "a"}


def test_uncompleted_selected_predecessor_blocks_join(conditional_definition: dict) -> None:
    """Planner 已选 predecessor 仍未完成时，Join 不得提前 ready。"""
    result = WorkflowDagJoinReadinessService.evaluate(
        definition=conditional_definition,
        node_id="join",
        completed_node_ids=set(),
        node_outputs={},
        predecessor_node_ids=("a",),
    )

    assert result.ready is False
    assert result.state_data is None
