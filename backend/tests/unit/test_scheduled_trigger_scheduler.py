from datetime import UTC, datetime

import pytest

from app.services.scheduled_trigger_scheduler import ScheduledTriggerScheduler


def test_interval_slot_is_stable_for_same_interval_window():
    now = datetime(2026, 8, 21, 0, 10, 37, tzinfo=UTC)
    assert ScheduledTriggerScheduler.interval_slot(now, 300) == ScheduledTriggerScheduler.interval_slot(
        datetime(2026, 8, 21, 0, 14, 59, tzinfo=UTC), 300
    )


def test_interval_slot_changes_at_interval_boundary():
    assert ScheduledTriggerScheduler.interval_slot(
        datetime(2026, 8, 21, 0, 4, 59, tzinfo=UTC), 300
    ) != ScheduledTriggerScheduler.interval_slot(
        datetime(2026, 8, 21, 0, 5, 0, tzinfo=UTC), 300
    )


def test_idempotency_key_is_deterministic_per_trigger_slot():
    trigger_id = "11111111-1111-1111-1111-111111111111"
    now = datetime(2026, 8, 21, 0, 10, 37, tzinfo=UTC)
    first = ScheduledTriggerScheduler.idempotency_key(trigger_id, now, 300)
    second = ScheduledTriggerScheduler.idempotency_key(trigger_id, now, 300)
    assert first == second
    assert first.startswith(f"scheduled:{trigger_id}:")


def test_idempotency_key_changes_for_next_slot():
    trigger_id = "11111111-1111-1111-1111-111111111111"
    first = ScheduledTriggerScheduler.idempotency_key(
        trigger_id, datetime(2026, 8, 21, 0, 4, 59, tzinfo=UTC), 300
    )
    second = ScheduledTriggerScheduler.idempotency_key(
        trigger_id, datetime(2026, 8, 21, 0, 5, 0, tzinfo=UTC), 300
    )
    assert first != second


def test_scheduler_rejects_non_positive_poll_interval():
    with pytest.raises(ValueError, match="poll_interval_seconds"):
        ScheduledTriggerScheduler(0)


def test_scheduler_rejects_invalid_interval_slot():
    with pytest.raises(ValueError, match="interval_seconds"):
        ScheduledTriggerScheduler.interval_slot(datetime.now(UTC), 0)
