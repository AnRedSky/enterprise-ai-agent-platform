"""Workflow Worker 领域公开入口。"""

from app.services.workflow_worker.durable_frontier_execution import PlannerDrivenDurableFrontierWorkflowWorker
from app.services.workflow_worker.frontier_runtime import DurableFrontierWorkflowWorker
from app.services.workflow_worker.lease_guard import (
    WorkflowWorkerLeaseGuard,
    WorkflowWorkerLeaseLost,
)
from app.services.workflow_worker.lease_runtime import LeaseAwareWorkflowWorker

# Planner-driven Worker 是当前 Durable Frontier 的正式默认入口。
# 它继承唯一 DurableFrontierWorkflowWorker 的 Claim、Lease 与 Runtime 能力，
# 仅在单次 Frontier 执行边界增加 Planner/异常收敛编排，不创建第二套 Execution 状态机。
WorkflowWorker = PlannerDrivenDurableFrontierWorkflowWorker

__all__ = [
    "WorkflowWorker",
    "PlannerDrivenDurableFrontierWorkflowWorker",
    "DurableFrontierWorkflowWorker",
    "WorkflowWorkerLeaseGuard",
    "WorkflowWorkerLeaseLost",
    "LeaseAwareWorkflowWorker",
]
