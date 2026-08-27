"""Workflow Durable Resume 自动恢复领域服务单元测试。

职责：验证 Recovery Policy、Checkpoint Candidate 与自动恢复结果/事件 Contract。
边界：禁止启动 Runtime；通过替换依赖验证 eligible / rejected / recovered / idempotency_hit。
关键依赖：WorkflowExecutionAutomaticRecoveryService、WorkflowRecoveryEventLogger、Resume Outcome Contract。
"""

from datetime import datetime
from types import SimpleNamespace
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


@pytest.mark.asyncio
async def test_evaluate_uses_resume_lineage_count_and_checkpoint_candidate(monkeypatch) -> None:
    service = WorkflowExecutionAutomaticRecoveryService(
        db=object(),
        policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0),
    )
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner=None, ended_at=datetime(2026, 8, 26, 11, 0), resume_of_execution_id=None,
    )
    checkpoint = SimpleNamespace(
        id=uuid4(), sequence=2, node_id="node-a", checkpoint_reason="node.completed",
        execution_status="running", node_status="completed", state_data={"value": 1},
        input_data={}, output_data={"value": 1},
    )

    async def fake_latest(execution_id):
        assert execution_id == execution.id
        return checkpoint

    async def fake_count(execution_item):
        assert execution_item is execution
        return 2

    monkeypatch.setattr(service.checkpoint, "latest", fake_latest)
    monkeypatch.setattr(service, "_count_resume_ancestors", fake_count)

    result = await service.evaluate(execution, now=datetime(2026, 8, 26, 12, 0))

    assert result.decision.eligible is True
    assert result.decision.reason_code == "eligible"
    assert result.decision.attempt_count == 2
    assert result.resume_execution_id is None
    assert result.outcome == "rejected"


@pytest.mark.asyncio
async def test_evaluate_rejects_active_worker_before_automatic_resume() -> None:
    service = WorkflowExecutionAutomaticRecoveryService(
        db=object(), policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0),
    )
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner="worker:active", ended_at=datetime(2026, 8, 26, 11, 0), resume_of_execution_id=None,
    )

    result = await service.evaluate(execution, now=datetime(2026, 8, 26, 12, 0))

    assert result.decision.eligible is False
    assert result.decision.reason_code == "worker_ownership_active"


@pytest.mark.asyncio
async def test_recover_emits_rejected_attempt_event() -> None:
    event_logger = _EventLogger()
    service = WorkflowExecutionAutomaticRecoveryService(
        db=object(), policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0), event_logger=event_logger,
    )
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner="worker:active", ended_at=datetime(2026, 8, 26, 11, 0), resume_of_execution_id=None,
    )

    result = await service.recover(execution, now=datetime(2026, 8, 26, 12, 0))

    assert result.outcome == "rejected"
    assert len(event_logger.events) == 1
    assert event_logger.events[0].event_name == RECOVERY_ATTEMPT
    assert event_logger.events[0].reason_code == "worker_ownership_active"
    assert event_logger.events[0].resume_execution_id is None


@pytest.mark.asyncio
async def test_recover_emits_created_attempt_event(monkeypatch) -> None:
    event_logger = _EventLogger()
    service = WorkflowExecutionAutomaticRecoveryService(
        db=object(), policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0), event_logger=event_logger,
    )
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner=None, ended_at=datetime(2026, 8, 26, 11, 0), resume_of_execution_id=None, created_by=uuid4(),
    )
    checkpoint = SimpleNamespace(
        id=uuid4(), sequence=2, node_id="node-a", checkpoint_reason="node.completed",
        execution_status="running", node_status="completed", state_data={}, input_data={}, output_data={},
    )

    async def fake_latest(_execution_id):
        return checkpoint

    async def fake_count(_execution):
        return 0

    monkeypatch.setattr(service.checkpoint, "latest", fake_latest)
    monkeypatch.setattr(service, "_count_resume_ancestors", fake_count)

    resume_execution = SimpleNamespace(id=uuid4())

    async def fake_resume(_execution, _actor):
        return WorkflowExecutionResumeOutcome(
            execution=resume_execution,
            outcome="created",
            idempotency_key="resume:key",
        )

    monkeypatch.setattr(service.resume_contract, "resume_with_outcome", fake_resume)

    result = await service.recover(execution, now=datetime(2026, 8, 26, 12, 0))

    assert result.outcome == "created"
    assert result.resume_execution_id == resume_execution.id
    assert event_logger.events[0].event_name == RECOVERY_ATTEMPT
    assert event_logger.events[0].reason_code == "eligible"


@pytest.mark.asyncio
async def test_recover_emits_idempotency_hit_attempt_event(monkeypatch) -> None:
    event_logger = _EventLogger()
    service = WorkflowExecutionAutomaticRecoveryService(
        db=object(), policy=WorkflowExecutionRecoveryPolicy(max_attempts=3, cooldown_seconds=0), event_logger=event_logger,
    )
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner=None, ended_at=datetime(2026, 8, 26, 11, 0), resume_of_execution_id=None, created_by=uuid4(),
    )
    checkpoint = SimpleNamespace(
        id=uuid4(), sequence=2, node_id="node-a", checkpoint_reason="node.completed",
        execution_status="running", node_status="completed", state_data={}, input_data={}, output_data={},
    )

    monkeypatch.setattr(service.checkpoint, "latest", lambda _execution_id: checkpoint)
    monkeypatch.setattr(service, "_count_resume_ancestors", lambda _execution: 0)

    existing_resume = SimpleNamespace(id=uuid4())

    async def fake_resume(_execution, _actor):
        return WorkflowExecutionResumeOutcome(
            execution=existing_resume,
            outcome="idempotency_hit",
            idempotency_key="resume:key",
        )

    monkeypatch.setattr(service.resume_contract, "resume_with_outcome", fake_resume)

    result = await service.recover(execution, now=datetime(2026, 8, 26, 12, 0))

    assert result.outcome == "idempotency_hit"
    assert result.resume_execution_id == existing_resume.id
    assert event_logger.events[0].event_name == RECOVERY_ATTEMPT
