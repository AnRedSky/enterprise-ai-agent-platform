"""Automatic Recovery 与统一 telemetry 的集成单元测试。"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.automatic import WorkflowExecutionAutomaticRecoveryService
from app.services.workflow.checkpoint.recovery.observability import RECOVERY_ATTEMPT, RECOVERY_TRACE_FINISHED, RECOVERY_TRACE_STARTED, WorkflowRecoveryEvent, WorkflowRecoveryTelemetry
from app.services.workflow.checkpoint.recovery.policy import WorkflowExecutionRecoveryDecision


@pytest.mark.asyncio
async def test_automatic_recovery_uses_one_trace_for_attempt_and_finish() -> None:
    trace_events: list[WorkflowRecoveryEvent] = []
    telemetry = WorkflowRecoveryTelemetry(trace_sink=trace_events.append)
    service = WorkflowExecutionAutomaticRecoveryService(db=None, telemetry=telemetry)  # type: ignore[arg-type]
    execution_id = uuid4(); resume_id = uuid4()

    async def evaluate(_execution, *, now=None):
        return SimpleNamespace(decision=WorkflowExecutionRecoveryDecision(eligible=True, reason_code="eligible", attempt_count=0, max_attempts=3))

    async def resume_with_outcome(_execution, _actor_id, *, commit=True):
        assert commit is False
        return SimpleNamespace(execution=SimpleNamespace(id=resume_id), outcome="created")

    async def link(*_args, **kwargs):
        assert kwargs["commit"] is False

    service.evaluate = evaluate  # type: ignore[method-assign]
    service.resume_contract.resume_with_outcome = resume_with_outcome  # type: ignore[method-assign]
    service.trace_link.link = link  # type: ignore[method-assign]
    service.db = SimpleNamespace(commit=lambda: None)
    execution = SimpleNamespace(id=execution_id, created_by=uuid4())

    async def commit():
        return None
    service.db.commit = commit
    result = await service.recover(execution)
    assert result.outcome == "created"
    assert [event.event_name for event in trace_events] == [RECOVERY_TRACE_STARTED, RECOVERY_ATTEMPT, RECOVERY_TRACE_FINISHED]
    assert trace_events[0].trace_id == trace_events[1].trace_id == trace_events[2].trace_id
    assert trace_events[1].resume_execution_id == trace_events[2].resume_execution_id == resume_id
    assert trace_events[1].phase == trace_events[2].phase == "automatic_recovery"
    assert trace_events[1].duration_ms is not None
    assert trace_events[2].duration_ms == trace_events[1].duration_ms


@pytest.mark.asyncio
async def test_automatic_recovery_rejection_also_closes_trace() -> None:
    trace_events: list[WorkflowRecoveryEvent] = []
    telemetry = WorkflowRecoveryTelemetry(trace_sink=trace_events.append)
    service = WorkflowExecutionAutomaticRecoveryService(db=None, telemetry=telemetry)  # type: ignore[arg-type]
    execution_id = uuid4()

    async def evaluate(_execution, *, now=None):
        return SimpleNamespace(decision=WorkflowExecutionRecoveryDecision(eligible=False, reason_code="checkpoint_not_eligible", attempt_count=1, max_attempts=3))

    service.evaluate = evaluate  # type: ignore[method-assign]
    execution = SimpleNamespace(id=execution_id, created_by=uuid4())
    result = await service.recover(execution)
    assert result.outcome == "rejected"
    assert [event.event_name for event in trace_events] == [RECOVERY_TRACE_STARTED, RECOVERY_ATTEMPT, RECOVERY_TRACE_FINISHED]
    assert trace_events[0].trace_id == trace_events[1].trace_id == trace_events[2].trace_id
    assert trace_events[2].outcome == "rejected"
    assert trace_events[2].reason_code == "checkpoint_not_eligible"
