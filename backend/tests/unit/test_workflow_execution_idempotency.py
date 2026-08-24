from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.services.workflow import WorkflowExecutionService


@pytest.fixture
def workflow_and_version():
    version = SimpleNamespace(id=uuid4(), status="published", definition={"nodes": [{"id": "input", "type": "input"}], "edges": []})
    workflow = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), published_version_id=version.id)
    return workflow, version


@pytest.mark.asyncio
async def test_create_returns_existing_execution_for_same_idempotency_key(workflow_and_version):
    workflow, version = workflow_and_version
    existing = SimpleNamespace(workflow_id=workflow.id, workflow_version_id=version.id)
    db = AsyncMock(); db.add = Mock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: existing)
    service = WorkflowExecutionService(db)
    result = await service.create(workflow, version, uuid4(), {"source": "retry-safe"}, "request-1")
    assert result is existing
    db.add.assert_not_called(); db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_rejects_reused_key_for_other_workflow(workflow_and_version):
    workflow, version = workflow_and_version
    existing = SimpleNamespace(workflow_id=uuid4(), workflow_version_id=version.id)
    db = AsyncMock(); db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: existing)
    service = WorkflowExecutionService(db)
    with pytest.raises(HTTPException) as exc:
        await service.create(workflow, version, uuid4(), {}, "request-1")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_handles_concurrent_idempotency_insert(workflow_and_version):
    workflow, version = workflow_and_version
    existing = SimpleNamespace(workflow_id=workflow.id, workflow_version_id=version.id)
    db = AsyncMock(); db.add = Mock()
    savepoint = AsyncMock(); db.begin_nested = Mock(return_value=savepoint)
    db.execute.side_effect = [SimpleNamespace(scalar_one_or_none=lambda: None), SimpleNamespace(scalar_one_or_none=lambda: existing)]
    db.flush.side_effect = IntegrityError("insert", {}, Exception("duplicate key"))
    service = WorkflowExecutionService(db)
    result = await service.create(workflow, version, uuid4(), {"source": "race"}, "request-1")
    assert result is existing
    db.begin_nested.assert_called_once()
    savepoint.__aenter__.assert_awaited_once(); savepoint.__aexit__.assert_awaited_once()
    assert db.execute.await_count == 2
