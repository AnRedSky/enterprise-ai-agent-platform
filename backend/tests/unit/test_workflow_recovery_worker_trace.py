from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


@pytest.mark.asyncio
async def test_get_trace_id_returns_persisted_recovery_lineage():
    db = AsyncMock()
    result = SimpleNamespace(scalar_one_or_none=lambda: "trace-123")
    db.execute = AsyncMock(return_value=result)
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4())

    trace_id = await WorkflowRecoveryTraceLinkService(db).get_trace_id(execution)

    assert trace_id == "trace-123"
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_trace_id_returns_none_when_execution_has_no_recovery_lineage():
    db = AsyncMock()
    result = SimpleNamespace(scalar_one_or_none=lambda: None)
    db.execute = AsyncMock(return_value=result)
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4())

    trace_id = await WorkflowRecoveryTraceLinkService(db).get_trace_id(execution)

    assert trace_id is None
    db.execute.assert_awaited_once()
