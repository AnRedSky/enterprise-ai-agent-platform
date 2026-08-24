"""Observability 领域服务单元测试。

职责：验证 Execution 生命周期与事件记录服务的标识、时间归一化行为。
边界：只测试 canonical Observability Service，不保留旧根 Service import。
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from app.models.execution import Execution
from app.services.observability import ObservabilityService


def test_observability_ids_are_unique():
    request_id, trace_id = ObservabilityService.new_ids()
    assert request_id != trace_id
    assert len(request_id) == 36
    assert len(trace_id) == 36


def test_observability_clock_returns_datetime():
    assert isinstance(ObservabilityService.now(), datetime)


async def test_finish_execution_accepts_naive_database_timestamp():
    execution = Execution(
        request_id="req",
        trace_id="trace",
        status="running",
        started_at=datetime.now(UTC),
    )
    db = AsyncMock()

    await ObservabilityService(db).finish_execution(execution)

    assert execution.status == "completed"
    assert execution.duration_ms is not None
    assert execution.duration_ms >= 0
    assert execution.ended_at is not None
    assert execution.ended_at.tzinfo is None


async def test_record_event_normalizes_database_timestamps_to_naive_utc():
    execution = Execution(
        id=uuid4(),
        request_id="req",
        trace_id="trace",
        status="running",
    )
    db = AsyncMock()
    started_at = datetime.now(UTC)

    event = await ObservabilityService(db).record_event(
        execution,
        span_type="model",
        started_at=started_at,
        model_id="mock-model",
    )

    assert event.started_at.tzinfo is None
    assert event.ended_at is not None
    assert event.ended_at.tzinfo is None
