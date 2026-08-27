from uuid import uuid4

from app.services.workflow.checkpoint.recovery.observability import WorkflowRecoveryEvent, WorkflowRecoveryTelemetry
from app.services.workflow_scheduler.trace import WorkflowSchedulerTraceService


def test_scheduler_scan_reuses_trace_id_for_completed_event_and_finish():
    events: list[WorkflowRecoveryEvent] = []
    telemetry = WorkflowRecoveryTelemetry(
        event_logger=None,
        trace_sink=events.append,
    )
    service = WorkflowSchedulerTraceService(telemetry)

    execution_id = uuid4()
    context = service.start_scan(execution_id=execution_id)
    service.finish_scan(
        context,
        candidates=3,
        eligible=2,
        recovered=1,
        rejected=1,
        contention=0,
        failed=0,
        duration_ms=12.5,
    )

    assert len(events) == 3
    assert events[0].trace_id == context.trace_id
    assert events[0].phase == "scheduler"
    assert events[1].event_name == "workflow.recovery.scan.completed"
    assert events[1].trace_id == context.trace_id
    assert events[1].candidates == 3
    assert events[1].eligible == 2
    assert events[1].recovered == 1
    assert events[2].trace_id == context.trace_id
    assert events[2].outcome == "completed"


def test_scheduler_scan_marks_finish_failed_when_scan_has_failures():
    events: list[WorkflowRecoveryEvent] = []
    telemetry = WorkflowRecoveryTelemetry(trace_sink=events.append)
    service = WorkflowSchedulerTraceService(telemetry)

    context = service.start_scan()
    service.finish_scan(context, failed=1)

    assert events[-1].trace_id == context.trace_id
    assert events[-1].outcome == "failed"
    assert events[-1].reason_code == "scheduler_scan_failed"
