from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


@pytest.mark.asyncio
async def test_trace_link_is_idempotent_and_does_not_store_runtime_state():
    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    source = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
    )
    resume = SimpleNamespace(
        id=uuid4(),
        tenant_id=source.tenant_id,
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        status="pending",
    )

    service = WorkflowRecoveryTraceLinkService(db)
    event = await service.link(source, resume, "trace-123", uuid4())

    assert event.execution_id == resume.id
    assert event.trace_id == "trace-123"
    assert event.event_type == service.EVENT_TYPE
    assert event.data == {
        "source_execution_id": str(source.id),
        "resume_execution_id": str(resume.id),
        "phase": "automatic_recovery",
    }
    assert "state_data" not in event.data
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_trace_link_returns_existing_event_without_duplicate_write():
    db = AsyncMock()
    existing = SimpleNamespace(id=uuid4(), trace_id="trace-existing")
    db.execute.return_value.scalar_one_or_none.return_value = existing

    source = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    resume = SimpleNamespace(
        id=uuid4(),
        tenant_id=source.tenant_id,
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        status="pending",
    )

    result = await WorkflowRecoveryTraceLinkService(db).link(source, resume, "trace-existing", uuid4())

    assert result is existing
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()
