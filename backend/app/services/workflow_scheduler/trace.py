"""Workflow Scheduler 与 Recovery Trace 的统一边界。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.services.workflow.checkpoint.recovery.observability import (
    RECOVERY_SCAN_COMPLETED,
    WorkflowRecoveryEvent,
    WorkflowRecoveryTelemetry,
)


@dataclass(frozen=True)
class SchedulerTraceContext:
    """一次 Scheduler scan 的稳定 trace 上下文。"""

    trace_id: str
    execution_id: UUID | None = None


class WorkflowSchedulerTraceService:
    """Scheduler trace 的轻量 facade。

    Scheduler 只负责产生 scan 生命周期事件；Recovery/Worker/Runtime 不在此模块实现。
    通过同一个 trace_id 将 Scheduler scan 与后续 Recovery 链路关联起来。
    """

    PHASE = "scheduler"

    def __init__(self, telemetry: WorkflowRecoveryTelemetry | None = None):
        self.telemetry = telemetry or WorkflowRecoveryTelemetry()

    def start_scan(
        self,
        *,
        execution_id: UUID | None = None,
        occurred_at: datetime | None = None,
    ) -> SchedulerTraceContext:
        trace_id = self.telemetry.start_trace(
            execution_id=execution_id,
            phase=self.PHASE,
            occurred_at=occurred_at,
        )
        return SchedulerTraceContext(trace_id=trace_id, execution_id=execution_id)

    def finish_scan(
        self,
        context: SchedulerTraceContext,
        *,
        candidates: int = 0,
        eligible: int = 0,
        recovered: int = 0,
        rejected: int = 0,
        contention: int = 0,
        failed: int = 0,
        duration_ms: float | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        self.telemetry.emit(
            WorkflowRecoveryEvent(
                event_name=RECOVERY_SCAN_COMPLETED,
                execution_id=context.execution_id,
                candidates=candidates,
                eligible=eligible,
                recovered=recovered,
                rejected=rejected,
                contention=contention,
                failed=failed,
                trace_id=context.trace_id,
                phase=self.PHASE,
                duration_ms=duration_ms,
                occurred_at=occurred_at,
            )
        )
        self.telemetry.finish_trace(
            context.trace_id,
            execution_id=context.execution_id,
            outcome="completed" if failed == 0 else "failed",
            reason_code="scheduler_scan_completed" if failed == 0 else "scheduler_scan_failed",
            phase=self.PHASE,
            duration_ms=duration_ms,
            occurred_at=occurred_at,
        )
