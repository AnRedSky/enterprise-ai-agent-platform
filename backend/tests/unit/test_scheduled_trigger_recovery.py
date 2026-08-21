from datetime import UTC, datetime

import pytest

from app.services.scheduled_trigger_scheduler import ScheduledTriggerScheduler


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
