from datetime import datetime, UTC
from unittest.mock import AsyncMock

from app.models.execution import Execution
from app.services.observability_service import ObservabilityService


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
    assert execution.ended_at.tzinfo is not None
