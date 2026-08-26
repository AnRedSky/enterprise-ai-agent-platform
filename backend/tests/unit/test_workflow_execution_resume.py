from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.workflow.checkpoint import WorkflowExecutionResumeAssessment
from app.services.workflow.execution import WorkflowExecutionService


@pytest.fixture
def resume_service() -> WorkflowExecutionService:
    db = SimpleNamespace(
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
        refresh=AsyncMock(),
        rollback=AsyncMock(),
        execute=AsyncMock(),
    )
    service = WorkflowExecutionService(db)  # type: ignore[arg-type]
    service.governance.audit = AsyncMock()
    service.governance.trace = AsyncMock()
    return service


def _source_execution(*, status: str = "failed", worker_owner: str | None = None):
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        created_by=uuid4(),
        status=status,
        worker_owner=worker_owner,
        input_data={"original": True},
    )


def _checkpoint(source):
    return SimpleNamespace(
        id=uuid4(),
        sequence=3,
        checkpoint_reason="node.completed",
        execution_status="running",
        node_status="completed",
        node_id="agent-1",
        state_data={"answer": "checkpoint-state"},
        input_data={"source": "node-input"},
        output_data={"answer": "checkpoint-state"},
        execution_id=source.id,
    )


def _assessment(source, checkpoint):
    return WorkflowExecutionResumeAssessment(
        eligible=True,
        reason_code="eligible",
        execution_id=source.id,
        workflow_version_id=source.workflow_version_id,
        checkpoint_id=checkpoint.id,
        checkpoint_sequence=checkpoint.sequence,
        node_id=checkpoint.node_id,
        state_data=dict(checkpoint.state_data),
        input_data=dict(checkpoint.input_data),
        output_data=dict(checkpoint.output_data),
        resume_idempotency_key=f"resume:{source.id}:checkpoint:{checkpoint.sequence}",
    )


@pytest.mark.asyncio
async def test_resume_creates_pending_execution_with_fixed_version_and_checkpoint_link(resume_service):
    source = _source_execution()
    checkpoint = _checkpoint(source)
    actor_id = uuid4()
    version = SimpleNamespace(id=source.workflow_version_id, definition={"config": {}, "nodes": []})
    resume_service._lock_execution = AsyncMock(return_value=source)
    resume_service.checkpoint.latest = AsyncMock(return_value=checkpoint)
    resume_service.checkpoint_recovery.assess = Mock(return_value=_assessment(source, checkpoint))
    resume_service.db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: version),
            SimpleNamespace(scalar_one_or_none=lambda: None),
        ]
    )

    result = await resume_service.resume_from_latest_checkpoint(source, actor_id)

    assert result.status == "pending"
    assert result.workflow_version_id == source.workflow_version_id
    assert result.workflow_id == source.workflow_id
    assert result.resume_of_execution_id == source.id
    assert result.resume_checkpoint_sequence == checkpoint.sequence
    assert result.idempotency_key == f"resume:{source.id}:checkpoint:{checkpoint.sequence}"
    assert result.input_data == checkpoint.state_data
    resume_service.governance.audit.assert_awaited()
    resume_service.governance.trace.assert_awaited()
    resume_service.db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_resume_is_idempotent_for_same_source_and_checkpoint(resume_service):
    source = _source_execution()
    checkpoint = _checkpoint(source)
    existing = SimpleNamespace(
        id=uuid4(),
        resume_of_execution_id=source.id,
        resume_checkpoint_sequence=checkpoint.sequence,
        status="pending",
    )
    version = SimpleNamespace(id=source.workflow_version_id, definition={"config": {}, "nodes": []})
    resume_service._lock_execution = AsyncMock(return_value=source)
    resume_service.checkpoint.latest = AsyncMock(return_value=checkpoint)
    resume_service.checkpoint_recovery.assess = Mock(return_value=_assessment(source, checkpoint))
    resume_service.db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: version),
            SimpleNamespace(scalar_one_or_none=lambda: existing),
        ]
    )

    result = await resume_service.resume_from_latest_checkpoint(source, uuid4())

    assert result is existing
    resume_service.db.commit.assert_not_awaited()
    resume_service.db.add.assert_not_called()


@pytest.mark.asyncio
async def test_resume_rejects_live_worker_ownership(resume_service):
    source = _source_execution(worker_owner="worker:live")
    resume_service._lock_execution = AsyncMock(return_value=source)
    resume_service.checkpoint.latest = AsyncMock(return_value=None)
    resume_service.checkpoint_recovery.assess = Mock(return_value=WorkflowExecutionResumeAssessment(
        eligible=False,
        reason_code="worker_ownership_active",
        execution_id=source.id,
        workflow_version_id=source.workflow_version_id,
    ))

    with pytest.raises(HTTPException) as exc:
        await resume_service.resume_from_latest_checkpoint(source, uuid4())

    assert exc.value.status_code == 409
    assert "worker_ownership_active" in str(exc.value.detail)
    resume_service.db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_resume_rejects_missing_or_invalid_checkpoint(resume_service):
    source = _source_execution()
    resume_service._lock_execution = AsyncMock(return_value=source)
    resume_service.checkpoint.latest = AsyncMock(return_value=None)
    resume_service.checkpoint_recovery.assess = Mock(return_value=WorkflowExecutionResumeAssessment(
        eligible=False,
        reason_code="checkpoint_missing",
        execution_id=source.id,
        workflow_version_id=source.workflow_version_id,
    ))

    with pytest.raises(HTTPException) as exc:
        await resume_service.resume_from_latest_checkpoint(source, uuid4())

    assert exc.value.status_code == 409
    assert "checkpoint_missing" in str(exc.value.detail)
    resume_service.db.commit.assert_not_awaited()
