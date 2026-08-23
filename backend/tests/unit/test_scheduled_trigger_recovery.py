from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler


def test_recovery_slots_are_bounded_and_include_current_slot():
    now = datetime(2026, 8, 21, 0, 10, 37, tzinfo=UTC)
    current = ScheduledTriggerScheduler.interval_slot(now, 300)
    assert ScheduledTriggerScheduler.recovery_slots(now, 300, max_recovery_slots=2) == [current - 1, current]


def test_recovery_key_is_stable_for_explicit_slot():
    trigger_id = "11111111-1111-1111-1111-111111111111"
    assert ScheduledTriggerScheduler.slot_idempotency_key(trigger_id, 42) == "scheduled:11111111-1111-1111-1111-111111111111:42"


def test_recovery_slots_reject_invalid_configuration():
    with pytest.raises(ValueError, match="max_recovery_slots"):
        ScheduledTriggerScheduler.recovery_slots(datetime.now(UTC), 300, max_recovery_slots=0)


def test_multi_worker_runtime_contention_is_not_scheduler_failure():
    exc = HTTPException(409, "只有 pending Execution 可以启动 Runtime")
    assert ScheduledTriggerScheduler.is_concurrent_runtime_claim(exc)


def test_unrelated_conflict_is_not_treated_as_contention():
    exc = HTTPException(409, "Trigger 已禁用")
    assert not ScheduledTriggerScheduler.is_concurrent_runtime_claim(exc)
