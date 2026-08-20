from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.workflow_execution import WorkflowExecutionService


@pytest.mark.asyncio
async def test_cancel_allows_pending_and_running_only():
    service = WorkflowExecutionService(AsyncMock())
    actor_id = uuid4()
    execution = SimpleNamespace(status="pending")

    result = await service.cancel(execution, actor_id)

    assert result.status == "cancelled"


@pytest.mark.asyncio
async def test_cancel_rejects_terminal_execution():
    service = WorkflowExecutionService(AsyncMock())
    execution = SimpleNamespace(status="completed")

    with pytest.raises(HTTPException) as exc:
        await service.cancel(execution, uuid4())

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_retry_creates_new_execution_with_lineage():
    db = AsyncMock()
    # AsyncSession.add() is synchronous; keep it as a regular Mock so the
    # test does not create an un-awaited coroutine while asserting persistence.
    db.add = Mock()
    version = SimpleNamespace(
        definition={
            "nodes": [
                {"id": "input", "type": "input"},
                {"id": "output", "type": "output"},
            ],
            "edges": [],
        }
    )
    # AsyncSession.execute() is awaited by the service, so configure the
    # awaited result rather than chaining through AsyncMock.return_value.
    db.execute.return_value = SimpleNamespace(scalar_one=lambda: version)
    service = WorkflowExecutionService(db)
    service.governance.audit = AsyncMock()
    service.governance.trace = AsyncMock()
    actor_id = uuid4()
    original_id = uuid4()
    execution = SimpleNamespace(
        id=original_id,
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        created_by=uuid4(),
        status="failed",
        input_data={"source": "retry"},
    )

    result = await service.retry(execution, actor_id)

    assert result.status == "pending"
    assert result.retry_of_execution_id == original_id
    assert result.workflow_id == execution.workflow_id
    assert result.workflow_version_id == execution.workflow_version_id
    assert result.input_data == execution.input_data
    db.add.assert_called_once_with(result)
    db.execute.assert_awaited_once()
    assert service.governance.trace.await_count == 2


@pytest.mark.asyncio
async def test_retry_rejects_non_failed_execution():
    service = WorkflowExecutionService(AsyncMock())
    execution = SimpleNamespace(status="cancelled")

    with pytest.raises(HTTPException) as exc:
        await service.retry(execution, uuid4())

    assert exc.value.status_code == 409
