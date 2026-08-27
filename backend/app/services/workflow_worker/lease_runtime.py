"""Worker Runtime 的租约失效集成入口。

职责：将 `WorkflowWorkerLeaseGuard` 正式接入默认 Worker Runtime，确保 heartbeat 明确失去
Execution ownership 后主动取消 `WorkflowExecutionService.run()`。
边界：复用 `runtime.WorkflowWorker` 的 claim、lease refresh、fencing、timeout、Recovery Trace
和 Runtime 执行逻辑；本模块不复制 Execution 状态机。
关键外部依赖：WorkflowWorker、WorkflowWorkerLeaseGuard。
"""

from __future__ import annotations

from uuid import UUID

from app.services.workflow_worker.lease_guard import (
    WorkflowWorkerLeaseGuard,
    WorkflowWorkerLeaseLost,
)
from app.services.workflow_worker.runtime import WorkflowWorker as BaseWorkflowWorker


class LeaseAwareWorkflowWorker(BaseWorkflowWorker):
    """带主动 Lease Loss Abort 能力的默认 Worker Runtime。"""

    async def _renew_lease_forever(self, execution_id: UUID) -> None:
        """由外层 LeaseGuard 统一监督 heartbeat，避免重复启动第二个监控循环。"""
        return None

    async def execute_claimed(self, execution_id: UUID) -> None:
        """在 LeaseGuard 监督下执行原有 Worker Runtime。"""
        guard = WorkflowWorkerLeaseGuard(
            renew_lease=lambda: self._renew_lease_once(execution_id),
            interval_seconds=max(0.1, self.lease_seconds / 3),
        )
        try:
            await guard.run(super().execute_claimed(execution_id))
        except WorkflowWorkerLeaseLost:
            # 旧 Worker 已失去 ownership；不得尝试继续修改 Execution。
            return
