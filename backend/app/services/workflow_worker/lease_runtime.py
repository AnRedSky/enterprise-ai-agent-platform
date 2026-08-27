"""Worker Runtime 的租约失效集成入口。

职责：将 `WorkflowWorkerLeaseGuard` 正式接入默认 Worker Runtime，确保 heartbeat 明确失去
Execution ownership 后主动取消 `WorkflowExecutionService.run()`。
边界：复用 `runtime.WorkflowWorker` 的 claim、lease refresh、fencing、timeout、Recovery Trace
和 Runtime 执行逻辑；本模块不复制 Execution 状态机。
关键外部依赖：WorkflowWorker、WorkflowWorkerLeaseGuard、WorkflowRecoveryTelemetry。
"""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from app.services.workflow.checkpoint.recovery.observability import (
    RECOVERY_WORKER_FINISHED,
    WorkflowRecoveryEvent,
    WorkflowRecoveryTelemetry,
)
from app.services.workflow_worker.lease_guard import (
    WorkflowWorkerLeaseGuard,
    WorkflowWorkerLeaseLost,
)
from app.services.workflow_worker.runtime import WorkflowWorker as BaseWorkflowWorker


class _LeaseAwareTelemetry:
    """在旧 Worker 被主动取消时修正其最终 Recovery outcome。"""

    def __init__(self, delegate: WorkflowRecoveryTelemetry, worker: "LeaseAwareWorkflowWorker") -> None:
        self.delegate = delegate
        self.worker = worker

    def emit(self, event: WorkflowRecoveryEvent, **kwargs: object) -> None:
        if event.event_name == RECOVERY_WORKER_FINISHED and self.worker._lease_lost:
            event = replace(
                event,
                outcome="aborted",
                reason_code="WORKER_LEASE_LOST",
            )
        self.delegate.emit(event, **kwargs)


class LeaseAwareWorkflowWorker(BaseWorkflowWorker):
    """带主动 Lease Loss Abort 能力的默认 Worker Runtime。"""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._lease_lost = False
        self._telemetry_delegate = self.telemetry
        self.telemetry = _LeaseAwareTelemetry(self._telemetry_delegate, self)

    async def _renew_lease_forever(self, execution_id: UUID) -> None:
        """由外层 LeaseGuard 统一监督 heartbeat，避免重复启动第二个监控循环。"""
        return None

    async def _renew_with_abort_signal(self, execution_id: UUID) -> bool:
        """刷新 lease，并把明确 ownership 丢失记录为 Runtime Abort 信号。"""
        owned = await self._renew_lease_once(execution_id)
        if not owned:
            self._lease_lost = True
        return owned

    async def execute_claimed(self, execution_id: UUID) -> None:
        """在 LeaseGuard 监督下执行原有 Worker Runtime。"""
        self._lease_lost = False
        guard = WorkflowWorkerLeaseGuard(
            renew_lease=lambda: self._renew_with_abort_signal(execution_id),
            interval_seconds=max(0.1, self.lease_seconds / 3),
        )
        try:
            await guard.run(super().execute_claimed(execution_id))
        except WorkflowWorkerLeaseLost:
            # 旧 Worker 已失去 ownership；不得尝试继续修改 Execution。
            return
