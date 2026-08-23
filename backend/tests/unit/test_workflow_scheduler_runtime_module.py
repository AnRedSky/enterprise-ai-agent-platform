from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler


def test_scheduler_runtime_module_keeps_existing_interval_slot_contract():
    scheduler = ScheduledTriggerScheduler(poll_interval_seconds=1, recovery_slots=2)
    assert scheduler.max_recovery_slots == 2
    assert scheduler.recovery_slots
