"""Workflow Worker 默认入口契约。

职责：验证公开 WorkflowWorker 是否指向当前正式的 Planner-driven Durable Frontier 入口。
边界：不验证 Worker 内部执行算法；具体 Claim、Lease 与 Delegation Runtime 路由由对应领域测试覆盖。
"""

from app.services.workflow_worker import PlannerDrivenDurableFrontierWorkflowWorker, WorkflowWorker


def test_default_workflow_worker_uses_planner_driven_durable_frontier_runtime() -> None:
    """默认 Worker 必须使用正式 Planner-driven Durable Frontier 入口。"""
    assert WorkflowWorker is PlannerDrivenDurableFrontierWorkflowWorker
