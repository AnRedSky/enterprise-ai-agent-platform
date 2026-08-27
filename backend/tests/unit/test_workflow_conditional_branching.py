"""Workflow Conditional Branching DAG Planner 单元测试。

职责：验证条件边、default、并行命中、未命中分支与有效 predecessor Contract。
边界：只验证纯内存 Planner，不连接数据库、Worker、Runtime 或 Provider。
关键依赖：WorkflowDagResumePlanner、WorkflowDagResumeRuntimePlanner、WorkflowDagContractValidator。
"""

import pytest

from app.services.workflow.checkpoint.recovery import WorkflowDagContractValidator, WorkflowDagResumePlanner, WorkflowDagResumeRuntimePlanner


def _definition() -> dict:
    return {
        "nodes": [
            {"id": "input", "type": "input", "config": {}},
            {"id": "approved", "type": "agent", "config": {}},
            {"id": "rejected", "type": "agent", "config": {}},
            {"id": "fallback", "type": "agent", "config": {}},
            {"id": "output", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "input", "target": "approved", "condition": {"op": "eq", "path": "result.status", "value": "approved"}},
            {"source": "input", "target": "rejected", "condition": {"op": "eq", "path": "result.status", "value": "rejected"}},
            {"source": "input", "target": "fallback", "default": True},
            {"source": "approved", "target": "output"},
            {"source": "rejected", "target": "output"},
            {"source": "fallback", "target": "output"},
        ],
    }


def test_conditional_edge_selects_matching_frontier() -> None:
    plan = WorkflowDagResumePlanner.plan(
        definition=_definition(),
        completed_node_ids={"input"},
        state_data_by_node={"input": {"result": {"status": "approved"}}},
    )
    assert plan.frontier_node_ids == ("approved",)
    assert plan.selected_predecessor_node_ids == (("approved", ("input",)),)


def test_default_edge_is_selected_when_no_condition_matches() -> None:
    plan = WorkflowDagResumePlanner.plan(
        definition=_definition(),
        completed_node_ids={"input"},
        state_data_by_node={"input": {"result": {"status": "pending"}}},
    )
    assert plan.frontier_node_ids == ("fallback",)


def test_multiple_matching_conditions_keep_definition_order() -> None:
    definition = _definition()
    definition["edges"] = [
        {"source": "input", "target": "approved", "condition": {"op": "eq", "path": "result.score", "value": 100}},
        {"source": "input", "target": "rejected", "condition": {"op": "gte", "path": "result.score", "value": 80}},
        {"source": "input", "target": "fallback", "default": True},
        {"source": "approved", "target": "output"},
        {"source": "rejected", "target": "output"},
        {"source": "fallback", "target": "output"},
    ]
    plan = WorkflowDagResumePlanner.plan(
        definition=definition,
        completed_node_ids={"input"},
        state_data_by_node={"input": {"result": {"score": 100}}},
    )
    assert plan.frontier_node_ids == ("approved", "rejected")


def test_unselected_branch_is_not_a_completed_join_predecessor() -> None:
    definition = _definition()
    plan = WorkflowDagResumePlanner.plan(
        definition=definition,
        completed_node_ids={"input", "approved"},
        state_data_by_node={"input": {"result": {"status": "approved"}}, "approved": {}},
    )
    assert plan.frontier_node_ids == ("output",)
    assert dict(plan.selected_predecessor_node_ids)["output"] == ("approved",)


def test_conditional_runtime_plan_uses_selected_predecessor_facts() -> None:
    plan = WorkflowDagResumeRuntimePlanner.plan(
        definition=_definition(),
        completed_node_ids={"input"},
        state_data={"result": {"status": "approved"}},
        state_data_by_node={"input": {"result": {"status": "approved"}}},
    )
    assert plan.frontier_node_ids == ("approved",)
    assert plan.selected_predecessor_node_ids == (("approved", ("input",)),)


def test_conditional_contract_rejects_mixed_unconditional_edges() -> None:
    definition = _definition()
    definition["edges"].append({"source": "input", "target": "output"})
    with pytest.raises(ValueError, match="混用无条件边"):
        WorkflowDagContractValidator.validate(definition=definition)


def test_conditional_contract_rejects_multiple_default_edges() -> None:
    definition = _definition()
    definition["edges"].insert(3, {"source": "input", "target": "output", "default": True})
    with pytest.raises(ValueError, match="最多一个 default"):
        WorkflowDagContractValidator.validate(definition=definition)


def test_conditional_planner_requires_persisted_source_state() -> None:
    with pytest.raises(ValueError, match="必须提供 completed Node state_data"):
        WorkflowDagResumePlanner.plan(definition=_definition(), completed_node_ids={"input"})
