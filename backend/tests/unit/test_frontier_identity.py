"""Durable Frontier Identity 的单元测试。

验证并发重建、Resume 重放与 Planner 遍历顺序变化时，等价 Node 集合仍收敛到同一个 Frontier identity。
"""

from __future__ import annotations

from uuid import uuid4

from app.services.workflow.frontier import WorkflowFrontierIdentity


def test_frontier_identity_is_order_independent_for_parallel_node_set() -> None:
    execution_id = uuid4()
    version_id = uuid4()
    first = WorkflowFrontierIdentity(
        execution_id=execution_id,
        workflow_version_id=version_id,
        decision_fingerprint="decision-a",
        node_ids=("node-c", "node-a", "node-b"),
    )
    reordered = WorkflowFrontierIdentity(
        execution_id=execution_id,
        workflow_version_id=version_id,
        decision_fingerprint="decision-a",
        node_ids=("node-b", "node-c", "node-a"),
    )

    assert first.key() == reordered.key()


def test_frontier_identity_keeps_execution_version_and_decision_in_key() -> None:
    execution_id = uuid4()
    version_id = uuid4()
    base = WorkflowFrontierIdentity(
        execution_id=execution_id,
        workflow_version_id=version_id,
        decision_fingerprint="decision-a",
        node_ids=("node-a", "node-b"),
    )

    assert base.key() != WorkflowFrontierIdentity(
        execution_id=uuid4(),
        workflow_version_id=version_id,
        decision_fingerprint="decision-a",
        node_ids=("node-a", "node-b"),
    ).key()
    assert base.key() != WorkflowFrontierIdentity(
        execution_id=execution_id,
        workflow_version_id=uuid4(),
        decision_fingerprint="decision-a",
        node_ids=("node-a", "node-b"),
    ).key()
    assert base.key() != WorkflowFrontierIdentity(
        execution_id=execution_id,
        workflow_version_id=version_id,
        decision_fingerprint="decision-b",
        node_ids=("node-a", "node-b"),
    ).key()
