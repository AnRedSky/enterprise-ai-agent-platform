"""Workflow Recovery 可观测事件模型单元测试。

职责：验证 Recovery 事件的字段标准化和敏感数据边界，不依赖数据库、HTTP 或外部 observability 服务。
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.services.workflow.checkpoint.recovery.observability import (
    RECOVERY_ATTEMPT,
    WorkflowRecoveryEvent,
    WorkflowRecoveryEventLogger,
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
