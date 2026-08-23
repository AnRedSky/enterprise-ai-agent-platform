from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.workflow_scheduler import (
    MisfirePolicy,
    ScheduleSlot,
    SchedulerState,
    SchedulerStatus,
    WorkflowScheduleContract,
    build_schedule_slot,
    choose_misfire_slots,
    lease_available,
    resolve_local_time,
)


TRIGGER_ID = uuid4()
WORKFLOW_ID = uuid4()
BASE_TIME = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)


def slot(hour: int) -> ScheduleSlot:
    return build_schedule_slot(TRIGGER_ID, BASE_TIME.replace(hour=hour))


def test_schedule_contract_requires_valid_timezone_and_utc_persistence():
    contract = WorkflowScheduleContract(
        trigger_id=TRIGGER_ID,
        workflow_id=WORKFLOW_ID,
        enabled=True,
        status=SchedulerStatus.ENABLED,
        timezone="Asia/Shanghai",
        schedule_expression="0 9 * * *",
        next_run_at=BASE_TIME,
        last_run_at=None,
        last_execution_id=None,
        lease_owner=None,
        lease_expires_at=None,
        misfire_policy=MisfirePolicy.SKIP,
        updated_at=BASE_TIME,
    )
    assert contract.timezone == "Asia/Shanghai"
    assert contract.next_run_at.tzinfo is timezone.utc


def test_schedule_contract_rejects_non_utc_next_run_at():
    with pytest.raises(ValueError, match="next_run_at.*UTC"):
        WorkflowScheduleContract(
            trigger_id=TRIGGER_ID,
            workflow_id=WORKFLOW_ID,
            enabled=True,
            status=SchedulerStatus.ENABLED,
            timezone="Asia/Shanghai",
            schedule_expression="0 9 * * *",
            next_run_at=datetime(2026, 8, 23, 9, 0),
            last_run_at=None,
            last_execution_id=None,
            lease_owner=None,
            lease_expires_at=None,
            misfire_policy=MisfirePolicy.SKIP,
            updated_at=BASE_TIME,
        )


def test_paused_state_keeps_scheduler_enabled_but_stops_execution_by_state():
    state = SchedulerState(status=SchedulerStatus.PAUSED)
    assert state.status is SchedulerStatus.PAUSED
    assert state.lease_owner is None


def test_disabled_state_requires_enabled_false():
    with pytest.raises(ValueError, match="disabled"):
        WorkflowScheduleContract(
            trigger_id=TRIGGER_ID,
            workflow_id=WORKFLOW_ID,
            enabled=True,
            status=SchedulerStatus.DISABLED,
            timezone="UTC",
            schedule_expression="0 9 * * *",
            next_run_at=BASE_TIME,
            last_run_at=None,
            last_execution_id=None,
            lease_owner=None,
            lease_expires_at=None,
            misfire_policy=MisfirePolicy.SKIP,
            updated_at=BASE_TIME,
        )


def test_schedule_slot_key_is_stable_and_utc_based():
    first = build_schedule_slot(TRIGGER_ID, datetime(2026, 8, 23, 8, 0, tzinfo=timezone.utc))
    second = build_schedule_slot(TRIGGER_ID, datetime(2026, 8, 23, 16, 0, tzinfo=timezone.utc))
    assert first.schedule_slot_key != second.schedule_slot_key
    assert first.schedule_slot_key == f"{TRIGGER_ID}:2026-08-23T08:00:00+00:00"


def test_lease_is_available_when_unowned_or_expired_but_not_when_active():
    assert lease_available(BASE_TIME, None)
    assert lease_available(BASE_TIME, BASE_TIME)
    assert lease_available(BASE_TIME, BASE_TIME.replace(hour=1)) is False


def test_misfire_skip_does_not_create_execution_slots():
    assert choose_misfire_slots([slot(1), slot(2)], MisfirePolicy.SKIP) == ()


def test_misfire_fire_once_creates_only_the_earliest_missed_slot():
    result = choose_misfire_slots([slot(3), slot(1), slot(2)], MisfirePolicy.FIRE_ONCE)
    assert result == (slot(1),)


def test_misfire_catch_up_is_bounded():
    result = choose_misfire_slots([slot(4), slot(1), slot(3), slot(2)], MisfirePolicy.CATCH_UP, catch_up_limit=2)
    assert result == (slot(1), slot(2))


def test_catch_up_requires_positive_limit():
    with pytest.raises(ValueError, match="catch_up_limit"):
        choose_misfire_slots([slot(1)], MisfirePolicy.CATCH_UP, catch_up_limit=0)


def test_dst_ambiguous_local_time_uses_first_occurrence():
    resolved = resolve_local_time(datetime(2026, 11, 1, 1, 30), "America/New_York")
    assert resolved == datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc)


def test_dst_nonexistent_local_time_is_rejected():
    with pytest.raises(ValueError, match="不存在时间"):
        resolve_local_time(datetime(2026, 3, 8, 2, 30), "America/New_York")


def test_lease_owner_and_expiry_must_be_paired():
    with pytest.raises(ValueError, match="lease_owner"):
        SchedulerState(
            status=SchedulerStatus.ENABLED,
            lease_owner="worker-a",
            lease_expires_at=None,
        )
