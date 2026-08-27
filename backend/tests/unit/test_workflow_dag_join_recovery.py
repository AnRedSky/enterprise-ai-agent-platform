"""DAG Multi-frontier Join Recovery 单元测试。"""

from copy import deepcopy

import pytest

from app.services.workflow.checkpoint.recovery.dag_join_recovery import WorkflowDagJoinRecoveryService


def _definition() -> dict:
    return {
        "nodes": [
            {"id": "branch-a", "type": "task"},
            {"id": "branch-b", "type": "task"},
            {"id": "join", "type": "join"},
        ],
        "edges": [
            {"source": "branch-a", "target": "join"},
            {"source": "branch-b", "target": "join"},
        ],
    }


def test_join_recovery_rebuilds_merged_state_from_durable_predecessors() -> None:
    """Recovery 必须从已完成 predecessor durable facts 重建 Join merged state。"""
    outputs = {
        "branch-a": {"a": 1},
        "branch-b": {"b": 2},
    }
    checkpoint_state = {"a": 1, "b": 2}

    readiness = WorkflowDagJoinRecoveryService.validate_checkpoint_state(
        definition=_definition(),
        node_id="join",
        completed_node_ids={"branch-a", "branch-b"},
        node_outputs=outputs,
        predecessor_node_ids=("branch-a", "branch-b"),
        checkpoint_state=checkpoint_state,
    )

    assert readiness.ready is True
    assert readiness.predecessor_node_ids == ("branch-a", "branch-b")
    assert readiness.state_data == checkpoint_state


def test_join_recovery_rejects_checkpoint_state_drift() -> None:
    """Checkpoint merged state 被篡改或漂移时必须拒绝 Recovery。"""
    with pytest.raises(ValueError, match="merged Checkpoint state"):
        WorkflowDagJoinRecoveryService.validate_checkpoint_state(
            definition=_definition(),
            node_id="join",
            completed_node_ids={"branch-a", "branch-b"},
            node_outputs={"branch-a": {"a": 1}, "branch-b": {"b": 2}},
            predecessor_node_ids=("branch-a", "branch-b"),
            checkpoint_state={"a": 1, "b": 999},
        )


def test_join_recovery_does_not_mutate_checkpoint_or_branch_state() -> None:
    """Recovery 校验只能读取快照，不得修改调用方传入 state。"""
    outputs = {"branch-a": {"nested": {"a": 1}}, "branch-b": {"b": 2}}
    checkpoint_state = {"nested": {"a": 1}, "b": 2}
    outputs_before = deepcopy(outputs)
    checkpoint_before = deepcopy(checkpoint_state)

    WorkflowDagJoinRecoveryService.validate_checkpoint_state(
        definition=_definition(),
        node_id="join",
        completed_node_ids={"branch-a", "branch-b"},
        node_outputs=outputs,
        predecessor_node_ids=("branch-a", "branch-b"),
        checkpoint_state=checkpoint_state,
    )

    assert outputs == outputs_before
    assert checkpoint_state == checkpoint_before


def test_join_recovery_rejects_uncompleted_predecessor() -> None:
    """缺少任一 Planner 选定 predecessor 的 durable completion 时不得恢复 Join。"""
    with pytest.raises(ValueError, match="尚未具备完整 predecessor"):
        WorkflowDagJoinRecoveryService.validate_checkpoint_state(
            definition=_definition(),
            node_id="join",
            completed_node_ids={"branch-a"},
            node_outputs={"branch-a": {"a": 1}},
            predecessor_node_ids=("branch-a", "branch-b"),
            checkpoint_state={"a": 1, "b": 2},
        )
