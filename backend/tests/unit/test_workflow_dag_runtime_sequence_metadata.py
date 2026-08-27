"""Workflow DAG 顺序 Resume 计划必须保留 Durable Decision metadata。"""

from __future__ import annotations

from app.services.workflow.checkpoint.recovery.dag_runtime_sequence import (
    WorkflowDagResumeRuntimeSequencePlanner,
)


def test_sequence_plan_preserves_fingerprint_and_selected_predecessors() -> None:
    definition = {
        "nodes": [
            {"id": "start", "type": "input", "config": {}},
            {"id": "next", "type": "output", "config": {}},
        ],
        "edges": [{"source": "start", "target": "next"}],
    }

    plans = WorkflowDagResumeRuntimeSequencePlanner.plan(
        definition=definition,
        completed_node_ids={"start"},
        state_data={"input": "resume"},
    )

    assert len(plans) == 1
    assert plans[0].decision_fingerprint
    assert plans[0].selected_predecessor_node_ids == (("next", ("start",)),)


def test_sequence_plan_carries_conditional_selected_predecessors() -> None:
    definition = {
        "nodes": [
            {"id": "start", "type": "input", "config": {}},
            {"id": "yes", "type": "output", "config": {}},
            {"id": "no", "type": "output", "config": {}},
        ],
        "edges": [
            {
                "source": "start",
                "target": "yes",
                "condition": {"op": "eq", "path": "approved", "value": True},
            },
            {"source": "start", "target": "no", "default": True},
        ],
    }

    plans = WorkflowDagResumeRuntimeSequencePlanner.plan(
        definition=definition,
        completed_node_ids={"start"},
        state_data={"approved": True},
        state_data_by_node={"start": {"approved": True}},
    )

    assert len(plans) == 1
    assert plans[0].frontier_node_id == "yes"
    assert plans[0].selected_predecessor_node_ids == (("yes", ("start",)),)
    assert plans[0].decision_fingerprint
