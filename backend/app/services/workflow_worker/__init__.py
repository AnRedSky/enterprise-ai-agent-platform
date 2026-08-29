"""Workflow Worker 领域公开入口。"""

from app.services.workflow_worker.durable_frontier_execution import PlannerDrivenDurableFrontierWorkflowWorker
from app.services.workflow_worker.frontier_runtime import DurableFrontierWorkflowWorker
from app.services.workflow_worker.lease_guard import (
    WorkflowWorkerLeaseGuard,
    WorkflowWorkerLeaseLost,
)
from app.services.workflow_worker.lease_runtime import LeaseAwareWorkflowWorker

# Durable Frontier 默认直接复用唯一的 Runtime execution 入口。
# PlannerDrivenDurableFrontierWorkflowWorker 是历史编排适配器，不作为生产默认入口，
# 避免与 runtime_entry.execute_claimed_execution 形成第二套 Execution/Delegation 状态机。
WorkflowWorker = DurableFrontierWorkflowWorker

__all__ = [
    "WorkflowWorker",
    "PlannerDrivenDurableFrontierWorkflowWorker",
    "DurableFrontierWorkflowWorker",
    "WorkflowWorkerLeaseGuard",
    "WorkflowWorkerLeaseLost",
    "LeaseAwareWorkflowWorker",
]
