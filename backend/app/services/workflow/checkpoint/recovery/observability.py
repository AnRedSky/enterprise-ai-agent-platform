"""Workflow Recovery 可观测事件模型。

职责：定义 Recovery Domain 与 Scheduler/Worker 共用的结构化事件字段，并提供统一日志/Trace/Metrics 出口。
边界：只负责事件建模与 telemetry dispatch，不负责数据库持久化或 provider 生命周期。
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Callable
from uuid import UUID, uuid4


RECOVERY_SCAN_COMPLETED = "workflow.recovery.scan.completed"
RECOVERY_ATTEMPT = "workflow.recovery.attempt"
RECOVERY_TRACE_STARTED = "workflow.recovery.trace.started"
RECOVERY_TRACE_FINISHED = "workflow.recovery.trace.finished"
RECOVERY_WORKER_STARTED = "workflow.recovery.worker.started"
RECOVERY_WORKER_FINISHED = "workflow.recovery.worker.finished"

TraceSink = Callable[["WorkflowRecoveryEvent"], None]
MetricsSink = Callable[["WorkflowRecoveryEvent"], None]


@dataclass(frozen=True)
class WorkflowRecoveryEvent:
    """单次 Recovery 可观测事件的稳定字段。"""

    event_name: str
    execution_id: UUID | None = None
    resume_execution_id: UUID | None = None
    outcome: str | None = None
    reason_code: str | None = None
    attempt_count: int | None = None
    max_attempts: int | None = None
    candidates: int | None = None
    eligible: int | None = None
    recovered: int | None = None
    rejected: int | None = None
    contention: int | None = None
    failed: int | None = None
    scan_limit: int | None = None
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    phase: str | None = None
    duration_ms: float | None = None
    occurred_at: datetime | None = None

    def to_log_fields(self) -> dict[str, object]:
        """转换为结构化日志字段，不包含 Checkpoint state_data 或 Secret。"""
        fields = asdict(self)
        fields = {key: value for key, value in fields.items() if value is not None}
        if self.occurred_at is not None:
            fields["occurred_at"] = self.occurred_at.isoformat()
        for key in ("execution_id", "resume_execution_id"):
            value = fields.get(key)
            if isinstance(value, UUID):
                fields[key] = str(value)
        return fields


class WorkflowRecoveryEventLogger:
    """Recovery 事件的统一日志出口。"""

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

    def emit(self, event: WorkflowRecoveryEvent, *, level: int = logging.INFO) -> None:
        self.logger.log(level, event.event_name, extra=event.to_log_fields())


class WorkflowRecoveryTelemetry:
    """Recovery 的统一 telemetry facade。

    Logger 始终输出结构化事件；Trace/Metrics 通过可选 sink 注入，避免 Recovery Domain
    直接依赖具体 OpenTelemetry、Prometheus 或云厂商 SDK。
    """

    def __init__(
        self,
        *,
        event_logger: WorkflowRecoveryEventLogger | None = None,
        trace_sink: TraceSink | None = None,
        metrics_sink: MetricsSink | None = None,
    ):
        self.event_logger = event_logger or WorkflowRecoveryEventLogger()
        self.trace_sink = trace_sink
        self.metrics_sink = metrics_sink

    def emit(self, event: WorkflowRecoveryEvent, *, level: int = logging.INFO) -> None:
        self.event_logger.emit(event, level=level)
        if self.trace_sink is not None:
            self.trace_sink(event)
        if self.metrics_sink is not None:
            self.metrics_sink(event)

    def start_trace(
        self,
        *,
        execution_id: UUID | None = None,
        resume_execution_id: UUID | None = None,
        phase: str = "recovery",
        occurred_at: datetime | None = None,
    ) -> str:
        """创建 Recovery trace，并发出统一 trace-start 事件。"""
        trace_id = uuid4().hex
        span_id = uuid4().hex[:16]
        self.emit(
            WorkflowRecoveryEvent(
                event_name=RECOVERY_TRACE_STARTED,
                execution_id=execution_id,
                resume_execution_id=resume_execution_id,
                trace_id=trace_id,
                span_id=span_id,
                phase=phase,
                occurred_at=occurred_at,
            )
        )
        return trace_id

    def finish_trace(
        self,
        trace_id: str,
        *,
        execution_id: UUID | None = None,
        resume_execution_id: UUID | None = None,
        outcome: str | None = None,
        reason_code: str | None = None,
        phase: str = "recovery",
        duration_ms: float | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        """结束 Recovery trace，并复用同一结构化事件模型。"""
        self.emit(
            WorkflowRecoveryEvent(
                event_name=RECOVERY_TRACE_FINISHED,
                execution_id=execution_id,
                resume_execution_id=resume_execution_id,
                outcome=outcome,
                reason_code=reason_code,
                trace_id=trace_id,
                span_id=uuid4().hex[:16],
                phase=phase,
                duration_ms=duration_ms,
                occurred_at=occurred_at,
            )
        )
