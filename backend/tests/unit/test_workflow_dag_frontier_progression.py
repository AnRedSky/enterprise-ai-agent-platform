"""DAG Frontier progression 单元测试。"""

from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.dag_frontier_progression import WorkflowDagFrontierProgressionService
from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlan


def _plan(*frontier: str) -> WorkflowDagResumeRuntimePlan:
    return WorkflowDagResumeRuntimePlan(
        completed_node_ids=("root",), frontier_node_ids=frontier,
        nodes=tuple({"id": node, "type": "agent", "config": {}} for node in frontier),
        state_data={"value": 1}, decision_fingerprint="current-decision",
    )


def test_plan_next_frontier_recomputes_identity_from_completed_facts() -> None:
    execution_id = uuid4()
    version_id = uuid4()
    definition = {
        "nodes": [
            {"id": "root", "type": "input", "config": {}},
            {"id": "a", "type": "agent", "config": {}},
            {"id": "b", "type": "agent", "config": {}},
        ],
        "edges": [{"source": "root", "target": "a"}, {"source": "root", "target": "b"}],
    }
    result = WorkflowDagFrontierProgressionService.plan_next_frontier(
        definition=definition, execution_id=execution_id, workflow_version_id=version_id,
        current_plan=_plan("root"), completed_node_ids={"root"}, state_data_by_node={"root": {"value": 1}},
    )
    assert result.resume_plan.frontier_node_ids == ("a", "b")
    assert result.identity is not None
    assert result.identity.execution_id == execution_id
    assert result.identity.workflow_version_id == version_id
    assert result.identity.node_ids == ("a", "b")
    assert result.identity.decision_fingerprint == result.resume_plan.decision_fingerprint


def test_plan_next_frontier_returns_terminal_without_identity() -> None:
    definition = {
        "nodes": [
            {"id": "root", "type": "input", "config": {}},
            {"id": "output", "type": "output", "config": {}},
        ],
        "edges": [{"source": "root", "target": "output"}],
    }
    result = WorkflowDagFrontierProgressionService.plan_next_frontier(
        definition=definition, execution_id=uuid4(), workflow_version_id=uuid4(),
        current_plan=WorkflowDagResumeRuntimePlan(
            completed_node_ids=("root", "output"), frontier_node_ids=("output",),
            nodes=({"id": "output", "type": "output", "config": {}},),
            state_data={"value": 1}, decision_fingerprint="terminal-decision",
        ),
        completed_node_ids={"root", "output"},
        state_data_by_node={"root": {"value": 1}, "output": {"value": 2}},
    )
    assert result.resume_plan.frontier_node_ids == ()
    assert result.identity is None


def test_plan_next_frontier_rejects_incomplete_current_frontier() -> None:
    definition = {
        "nodes": [{"id": "root", "type": "input", "config": {}}, {"id": "a", "type": "agent", "config": {}}],
        "edges": [{"source": "root", "target": "a"}],
    }
    with pytest.raises(ValueError, match="尚未全部形成 completed durable facts"):
        WorkflowDagFrontierProgressionService.plan_next_frontier(
            definition=definition, execution_id=uuid4(), workflow_version_id=uuid4(),
            current_plan=_plan("a"), completed_node_ids={"root"}, state_data_by_node={"root": {"value": 1}},
        )
