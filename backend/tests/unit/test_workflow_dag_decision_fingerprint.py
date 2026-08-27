from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner


def _definition():
    return {
        "nodes": [
            {"id": "start", "type": "agent"},
            {"id": "yes", "type": "agent"},
            {"id": "no", "type": "agent"},
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


def test_same_durable_facts_produce_same_decision_fingerprint():
    first = WorkflowDagResumePlanner.plan(
        definition=_definition(),
        completed_node_ids={"start"},
        state_data_by_node={"start": {"approved": True, "request_id": "r-1"}},
    )
    second = WorkflowDagResumePlanner.plan(
        definition=_definition(),
        completed_node_ids={"start"},
        state_data_by_node={"start": {"request_id": "r-1", "approved": True}},
    )

    assert first.frontier_node_ids == ("yes",)
    assert second.frontier_node_ids == ("yes",)
    assert first.decision_fingerprint == second.decision_fingerprint


def test_changed_condition_state_produces_different_decision_fingerprint():
    approved = WorkflowDagResumePlanner.plan(
        definition=_definition(),
        completed_node_ids={"start"},
        state_data_by_node={"start": {"approved": True}},
    )
    rejected = WorkflowDagResumePlanner.plan(
        definition=_definition(),
        completed_node_ids={"start"},
        state_data_by_node={"start": {"approved": False}},
    )

    assert approved.frontier_node_ids == ("yes",)
    assert rejected.frontier_node_ids == ("no",)
    assert approved.decision_fingerprint != rejected.decision_fingerprint
