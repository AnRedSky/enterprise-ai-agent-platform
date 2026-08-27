"""Workflow Recovery 可观测事件模型单元测试。

职责：验证 Recovery 事件字段标准化、Trace/Metrics fan-out 和敏感数据边界。
不依赖数据库、HTTP、OpenTelemetry 或外部 metrics 服务。
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.services.workflow.checkpoint.recovery.observability import (
    RECOVERY_ATTEMPT,
    RECOVERY_TRACE_FINISHED,
    RECOVERY_TRACE_STARTED,
    WorkflowRecoveryEvent,
    WorkflowRecoveryEventLogger,
    WorkflowRecoveryTelemetry,
)


def test_recovery_event_serializes_stable_fields() -> None:
    execution_id = uuid4()
    resume_id = uuid4()
    occurred_at = datetime(2026, 8, 27, 1, 2, 3, tzinfo=UTC)

    event = WorkflowRecoveryEvent(
        event_name=RECOVERY_ATTEMPT,
        execution_id=execution_id,
        resume_execution_id=resume_id,
        reason_code="recovered",
        attempt_count=1,
        max_attempts=3,
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="parent-1",
        phase="resume",
        duration_ms=12.5,
        occurred_at=occurred_at,
    )

    fields = event.to_log_fields()

    assert fields == {
        "event_name": RECOVERY_ATTEMPT,
        "execution_id": str(execution_id),
        "resume_execution_id": str(resume_id),
        "reason_code": "recovered",
        "attempt_count": 1,
        "max_attempts": 3,
        "trace_id": "trace-1",
        "span_id": "span-1",
        "parent_span_id": "parent-1",
        "phase": "resume",
        "duration_ms": 12.5,
        "occurred_at": occurred_at.isoformat(),
    }
    assert "state_data" not in fields
    assert "secret" not in fields


def test_recovery_event_logger_emits_event_fields(caplog) -> None:
    logger = WorkflowRecoveryEventLogger()
    execution_id = uuid4()

    caplog.set_level("INFO", logger=logger.logger.name)
    logger.emit(
        WorkflowRecoveryEvent(
            event_name=RECOVERY_ATTEMPT,
            execution_id=execution_id,
            reason_code="recovery_cooldown_active",
        )
    )

    record = caplog.records[-1]
    assert record.message == RECOVERY_ATTEMPT
    assert record.execution_id == str(execution_id)
    assert record.reason_code == "recovery_cooldown_active"


def test_recovery_telemetry_fans_out_same_event_to_trace_and_metrics() -> None:
    trace_events: list[WorkflowRecoveryEvent] = []
    metrics_events: list[WorkflowRecoveryEvent] = []
    telemetry = WorkflowRecoveryTelemetry(
        trace_sink=trace_events.append,
        metrics_sink=metrics_events.append,
    )
    event = WorkflowRecoveryEvent(event_name=RECOVERY_ATTEMPT)

    telemetry.emit(event)

    assert trace_events == [event]
    assert metrics_events == [event]


def test_recovery_telemetry_trace_lifecycle_preserves_trace_id() -> None:
    events: list[WorkflowRecoveryEvent] = []
    telemetry = WorkflowRecoveryTelemetry(trace_sink=events.append)

    trace_id = telemetry.start_trace(phase="automatic_recovery")
    telemetry.finish_trace(
        trace_id,
        outcome="recovered",
        reason_code="checkpoint_available",
        phase="automatic_recovery",
        duration_ms=4.2,
    )

    assert len(events) == 2
    assert events[0].event_name == RECOVERY_TRACE_STARTED
    assert events[1].event_name == RECOVERY_TRACE_FINISHED
    assert events[0].trace_id == trace_id
    assert events[1].trace_id == trace_id
    assert events[1].outcome == "recovered"
    assert events[1].duration_ms == 4.2
