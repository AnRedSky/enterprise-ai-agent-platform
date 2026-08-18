from datetime import datetime

from app.services.observability_service import ObservabilityService


def test_observability_ids_are_unique():
    request_id, trace_id = ObservabilityService.new_ids()
    assert request_id != trace_id
    assert len(request_id) == 36
    assert len(trace_id) == 36


def test_observability_clock_returns_datetime():
    assert isinstance(ObservabilityService.now(), datetime)
