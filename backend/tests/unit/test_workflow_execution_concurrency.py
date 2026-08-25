from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.workflow import WorkflowExecutionService


@pytest.mark.asyncio
async def test_lock_execution_uses_for_update_for_real_async_session():
    execution = SimpleNamespace(id=uuid4(), worker_owner=None)
    db = object.__new__(AsyncSession)
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: execution))
    service = WorkflowExecutionService(db)

    result = await service._lock_execution(execution)

    assert result is execution
    statement = db.execute.await_args.args[0]
    assert statement._for_update_arg is not None


@pytest.mark.asyncio
async def test_transition_rechecks_locked_state_before_applying_change():
    stale = SimpleNamespace(id=uuid4(), status="pending", worker_owner=None)
    locked = SimpleNamespace(id=stale.id, tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(),
                             created_by=uuid4(), status="cancelled", current_node_id=None, started_at=None,
                             ended_at=None, output_data=None, error_code=None, error_message=None,
                             worker_owner=None)
    db = object.__new__(AsyncSession)
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: locked))
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    service = WorkflowExecutionService(db)

    with pytest.raises(Exception) as exc:
        await service.transition(stale, "running")

    assert getattr(exc.value, "status_code", None) == 409
    db.commit.assert_not_awaited()
