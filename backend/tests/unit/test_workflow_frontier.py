from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.workflow.frontier import (
    WorkflowFrontierIdentity,
    WorkflowFrontierStatus,
    transition_frontier,
)


def test_frontier_identity_is_deterministic_for_same_ordered_nodes() -> None:
    execution_id = uuid4()
    version_id = uuid4()
    first = WorkflowFrontierIdentity(execution_id, version_id, "decision-a", ("node-a", "node-b"))
    second = WorkflowFrontierIdentity(execution_id, version_id, "decision-a", ("node-a", "node-b"))

    assert first.key() == second.key()


def test_frontier_identity_canonicalizes_node_order() -> None:
    execution_id = uuid4()
    version_id = uuid4()
    first = WorkflowFrontierIdentity(execution_id, version_id, "decision-a", ("node-a", "node-b"))
    second = WorkflowFrontierIdentity(execution_id, version_id, "decision-a", ("node-b", "node-a"))

    # Frontier identity 表示并行 Node 集合而非执行顺序；执行顺序仍由 node_ids 原值交给 Executor。
    assert first.key() == second.key()


def test_frontier_lifecycle_allows_claim_run_complete() -> None:
    status = WorkflowFrontierStatus.PENDING
    status = transition_frontier(status, WorkflowFrontierStatus.CLAIMED).target
    status = transition_frontier(status, WorkflowFrontierStatus.RUNNING).target
    status = transition_frontier(status, WorkflowFrontierStatus.COMPLETED).target

    assert status is WorkflowFrontierStatus.COMPLETED


def test_frontier_terminal_state_cannot_be_reclaimed() -> None:
    with pytest.raises(ValueError, match="非法 Frontier 状态转换"):
        transition_frontier(WorkflowFrontierStatus.COMPLETED, WorkflowFrontierStatus.CLAIMED)
