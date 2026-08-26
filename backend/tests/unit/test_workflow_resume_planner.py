from __future__ import annotations

import pytest

from app.services.workflow.checkpoint.recovery import WorkflowExecutionResumePlanner


def _definition() -> dict:
    return {
        "config": {"timeout_ms": 5000},
        "nodes": [
            {"id": "input", "type": "input", "config": {}},
            {"id": "agent", "type": "agent", "config": {"agent_id": "agent-1"}},
            {"id": "output", "type": "output", "config": {}},
        ],
    }


def test_resume_planner_starts_after_completed_checkpoint_node() -> None:
    plan = WorkflowExecutionResumePlanner.plan(
        definition=_definition(),
        checkpoint_node_id="agent",
        checkpoint_sequence=2,
        state_data={"content": "checkpoint-result"},
    )

    assert plan.checkpoint_node_id == "agent"
    assert plan.checkpoint_sequence == 2
    assert plan.state_data == {"content": "checkpoint-result"}
    assert [node["id"] for node in plan.remaining_nodes] == ["output"]


def test_resume_planner_deep_copies_state_and_remaining_nodes() -> None:
    definition = _definition()
    state = {"nested": {"value": 1}}

    plan = WorkflowExecutionResumePlanner.plan(
        definition=definition,
        checkpoint_node_id="input",
        checkpoint_sequence=1,
        state_data=state,
    )

    state["nested"]["value"] = 99
    definition["nodes"][1]["config"]["agent_id"] = "changed"

    assert plan.state_data == {"nested": {"value": 1}}
    assert plan.remaining_nodes[0]["config"]["agent_id"] == "agent-1"


@pytest.mark.parametrize(
    ("checkpoint_node_id", "checkpoint_sequence", "state_data", "message"),
    [
        ("missing", 0, {}, "Checkpoint node_id 必须在 Workflow Definition 中唯一存在"),
        ("agent", -1, {}, "Checkpoint sequence 无效"),
        ("agent", 0, [], "Checkpoint state_data 必须为对象"),
    ],
)
def test_resume_planner_rejects_invalid_boundary(
    checkpoint_node_id: str,
    checkpoint_sequence: int,
    state_data,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        WorkflowExecutionResumePlanner.plan(
            definition=_definition(),
            checkpoint_node_id=checkpoint_node_id,
            checkpoint_sequence=checkpoint_sequence,
            state_data=state_data,
        )


def test_resume_planner_rejects_duplicate_checkpoint_node_id() -> None:
    definition = _definition()
    definition["nodes"].append({"id": "agent", "type": "output", "config": {}})

    with pytest.raises(ValueError, match="Checkpoint node_id 必须在 Workflow Definition 中唯一存在"):
        WorkflowExecutionResumePlanner.plan(
            definition=definition,
            checkpoint_node_id="agent",
            checkpoint_sequence=2,
            state_data={},
        )
