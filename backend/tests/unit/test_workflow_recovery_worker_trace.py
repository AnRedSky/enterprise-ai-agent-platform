from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


@pytest.mark.asyncio
async def test_get_trace_id_returns_persisted_recovery_lineage():
    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none.return_value = "trace-123"
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4())

    trace_id = await WorkflowRecoveryTraceLinkService(db).get_trace_id(execution)

    assert trace_id == "trace-123"
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_trace_id_returns_none_when_execution_has_no_recovery_lineage():
    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4())

    trace_id = await WorkflowRecoveryTraceLinkService(db).get_trace_id(execution)

    assert trace_id is None
    db.execute.assert_awaited_once()
