from app.services.workflow.checkpoint.recovery.observability import WorkflowRecoveryEvent, WorkflowRecoveryTelemetry
from app.services.workflow_scheduler.runtime_trace import TracedScheduledTriggerScheduler
from app.services.workflow_scheduler.trace import WorkflowSchedulerTraceService


class _FakeScheduler(TracedScheduledTriggerScheduler):
    async def tick_once(self, now=None):
        return await super().tick_once(now=now)


async def test_traced_scheduler_runtime_wraps_tick_once(monkeypatch):
    events: list[WorkflowRecoveryEvent] = []
    telemetry = WorkflowRecoveryTelemetry(event_logger=None, trace_sink=events.append)
    service = WorkflowSchedulerTraceService(telemetry)
    scheduler = TracedScheduledTriggerScheduler(
        poll_interval_seconds=1,
        recovery_slots=1,
        lease_seconds=1,
        trace_service=service,
    )

    async def fake_tick_once(now=None):
        return {
            "eligible": 2,
            "dispatched": 1,
            "skipped": 0,
            "failed": 0,
            "recovered": 1,
            "contention": 0,
        }

    monkeypatch.setattr(scheduler.__class__.__bases__[0], "tick_once", fake_tick_once)

    result = await scheduler.tick_once()

    assert result["dispatched"] == 1
    assert len(events) == 3
    assert events[0].trace_id == events[-1].trace_id
    assert events[1].event_name == "workflow.recovery.scan.completed"
    assert events[1].recovered == 1
    assert events[-1].outcome == "completed"


async def test_traced_scheduler_runtime_finishes_failed_scan(monkeypatch):
    events: list[WorkflowRecoveryEvent] = []
    telemetry = WorkflowRecoveryTelemetry(event_logger=None, trace_sink=events.append)
    service = WorkflowSchedulerTraceService(telemetry)
    scheduler = TracedScheduledTriggerScheduler(
        poll_interval_seconds=1,
        recovery_slots=1,
        lease_seconds=1,
        trace_service=service,
    )

    async def fake_tick_once(now=None):
        raise RuntimeError("scheduler failure")

    monkeypatch.setattr(scheduler.__class__.__bases__[0], "tick_once", fake_tick_once)

    try:
        await scheduler.tick_once()
    except RuntimeError:
        pass
    else:
        raise AssertionError("scheduler failure must propagate")

    assert events[0].trace_id == events[-1].trace_id
    assert events[-1].outcome == "failed"
    assert events[-1].reason_code == "scheduler_scan_failed"
