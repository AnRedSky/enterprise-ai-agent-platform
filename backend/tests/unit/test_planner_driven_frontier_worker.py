"""PlannerDriven Durable Frontier Worker 的单元契约测试。

职责：验证默认 Worker 入口与 Planner-driven dispatch 边界，避免测试复制生产执行算法。
"""

from app.services.workflow_worker import (
    DurableFrontierWorkflowWorker,
    PlannerDrivenDurableFrontierWorkflowWorker,
    WorkflowWorker,
)


def test_workflow_worker_uses_planner_driven_frontier_worker():
    """默认 Worker 必须使用 Planner-driven Durable Frontier 入口。"""
    assert WorkflowWorker is PlannerDrivenDurableFrontierWorkflowWorker


def test_planner_driven_worker_reuses_frontier_worker_contract():
    """Planner-driven Worker 必须复用既有 Frontier Claim、Lease 与 Dispatch 契约。"""
    assert issubclass(PlannerDrivenDurableFrontierWorkflowWorker, DurableFrontierWorkflowWorker)
    assert hasattr(PlannerDrivenDurableFrontierWorkflowWorker, "claim_one_frontier")
    assert hasattr(PlannerDrivenDurableFrontierWorkflowWorker, "dispatch_once")
    assert hasattr(PlannerDrivenDurableFrontierWorkflowWorker, "execute_frontier")
