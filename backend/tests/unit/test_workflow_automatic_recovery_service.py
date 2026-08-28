"""Workflow Durable Resume 自动恢复领域服务单元测试。"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.automatic import WorkflowExecutionAutomaticRecoveryService
from app.services.workflow.checkpoint.recovery.observability import RECOVERY_ATTEMPT
from app.services.workflow.checkpoint.recovery.policy import WorkflowExecutionRecoveryPolicy
from app.services.workflow.checkpoint.recovery.resume_contract import WorkflowExecutionResumeOutcome


class _EventLogger:
    def __init__(self):
        self.events = []
    def emit(self, event, *, level=20):
        self.events.append(event)


def _checkpoint(execution_id):
    return SimpleNamespace(
        id=uuid4(), execution_id=execution_id, sequence=2, node_id="node-a", checkpoint_reason="node.completed",
        execution_status="running", node_status="completed", state_data={"value": 1}, input_data={}, output_data={"value": 1},
    )


@pytest.mark.asyncio
async def test_evaluate_uses_resume_lineage_count_and_checkpoint_candidate(monkeypatch) -> None:
    db = AsyncMock()
    service = WorkflowExecutionAutomaticRecoveryService(db=db, policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0))
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4(), status="failed", worker_owner=None, ended_at=datetime(2026, 8, 26, 11, 0), resume_of_execution_id=None)
    checkpoint = _checkpoint(execution.id)

    async def fake_latest(execution_id, *, tenant_id=None):
        assert execution_id == execution.id; assert tenant_id == execution.tenant_id
        return checkpoint
    async def fake_count(execution_item):
        assert execution_item is execution
        return 2
    monkeypatch.setattr(service.checkpoint, "latest_recovery_fact", fake_latest)
    monkeypatch.setattr(service, "_count_resume_ancestors", fake_count)
    result = await service.evaluate(execution, now=datetime(2026, 8, 26, 12, 0))
    assert result.decision.eligible is True
    assert result.decision.reason_code == "eligible"
    assert result.decision.attempt_count == 2
    assert result.resume_execution_id is None
    assert result.outcome == "rejected"


@pytest.mark.asyncio
async def test_evaluate_rejects_active_worker_before_automatic_resume() -> None:
    service = WorkflowExecutionAutomaticRecoveryService(db=object(), policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0))
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4(), status="failed", worker_owner="worker:active", ended_at=datetime(2026, 8, 26, 11, 0), resume_of_execution_id=None)
    result = await service.evaluate(execution, now=datetime(2026, 8, 26, 12, 0))
    assert result.decision.eligible is False
    assert result.decision.reason_code == "worker_ownership_active"


@pytest.mark.asyncio
async def test_recover_emits_rejected_attempt_event() -> None:
    event_logger = _EventLogger()
    service = WorkflowExecutionAutomaticRecoveryService(db=object(), policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0), event_logger=event_logger)
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4(), status="failed", worker_owner="worker:active", ended_at=datetime(2026, 8, 26, 11, 0), resume_of_execution_id=None)
    result = await service.recover(execution, now=datetime(2026, 8, 26, 12, 0))
    attempts = [event for event in event_logger.events if event.event_name == RECOVERY_ATTEMPT]
    assert result.outcome == "rejected"
    assert len(attempts) == 1
    assert attempts[0].reason_code == "worker_ownership_active"
    assert attempts[0].resume_execution_id is None


@pytest.mark.asyncio
async def test_recover_emits_created_attempt_event(monkeypatch) -> None:
    event_logger = _EventLogger(); db = AsyncMock()
    service = WorkflowExecutionAutomaticRecoveryService(db=db, policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0), event_logger=event_logger)
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4(), status="failed", worker_owner=None, ended_at=datetime(2026, 8, 26, 11, 0), resume_of_execution_id=None, created_by=uuid4())
    checkpoint = _checkpoint(execution.id)
    async def fake_latest(_execution_id, *, tenant_id=None): return checkpoint
    async def fake_count(_execution): return 0
    monkeypatch.setattr(service.checkpoint, "latest_recovery_fact", fake_latest)
    monkeypatch.setattr(service, "_count_resume_ancestors", fake_count)
    resume_execution = SimpleNamespace(id=uuid4())
    async def fake_resume(_execution, _actor, *, commit=True):
        assert commit is False
        return WorkflowExecutionResumeOutcome(execution=resume_execution, outcome="created", idempotency_key="resume:key")
    async def fake_trace_link(*_args, **kwargs):
        assert kwargs["commit"] is False
        return SimpleNamespace()
    monkeypatch.setattr(service.resume_contract, "resume_with_outcome", fake_resume)
    monkeypatch.setattr(service.trace_link, "link", fake_trace_link)
    result = await service.recover(execution, now=datetime(2026, 8, 26, 12, 0))
    attempts = [event for event in event_logger.events if event.event_name == RECOVERY_ATTEMPT]
    assert result.outcome == "created"
    assert result.resume_execution_id == resume_execution.id
    assert len(attempts) == 1
    assert attempts[0].reason_code == "eligible"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_recover_emits_idempotency_hit_attempt_event(monkeypatch) -> None:
    event_logger = _EventLogger(); db = AsyncMock()
    service = WorkflowExecutionAutomaticRecoveryService(db=db, policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0), event_logger=event_logger)
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4(), status="failed", worker_owner=None, ended_at=datetime(2026, 8, 26, 11, 0), resume_of_execution_id=None, created_by=uuid4())
    checkpoint = _checkpoint(execution.id)
    async def fake_latest(_execution_id, *, tenant_id=None): return checkpoint
    monkeypatch.setattr(service.checkpoint, "latest_recovery_fact", fake_latest)
    monkeypatch.setattr(service, "_count_resume_ancestors", lambda _execution: 0)
    existing_resume = SimpleNamespace(id=uuid4())
    async def fake_resume(_execution, _actor, *, commit=True):
        assert commit is False
        return WorkflowExecutionResumeOutcome(execution=existing_resume, outcome="idempotency_hit", idempotency_key="resume:key")
    async def fake_trace_link(*_args, **kwargs):
        assert kwargs["commit"] is False
        return SimpleNamespace()
    monkeypatch.setattr(service.resume_contract, "resume_with_outcome", fake_resume)
    monkeypatch.setattr(service.trace_link, "link", fake_trace_link)
    result = await service.recover(execution, now=datetime(2026, 8, 26, 12, 0))
    attempts = [event for event in event_logger.events if event.event_name == RECOVERY_ATTEMPT]
    assert result.outcome == "idempotency_hit"
    assert result.resume_execution_id == existing_resume.id
    assert len(attempts) == 1
    assert attempts[0].event_name == RECOVERY_ATTEMPT
