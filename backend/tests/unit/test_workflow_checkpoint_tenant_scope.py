from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


@pytest.mark.asyncio
async def test_checkpoint_latest_applies_explicit_tenant_scope():
    db = AsyncMock()
    db.execute.return_value = type("Result", (), {"scalar_one_or_none": lambda self: None})()
    service = WorkflowExecutionCheckpointService(db)
    execution_id = uuid4()
    tenant_id = uuid4()

    assert await service.latest(execution_id, tenant_id=tenant_id) is None
    query = db.execute.call_args.args[0]
    sql = str(query)
    assert "workflow_execution_checkpoints.execution_id" in sql
    assert "workflow_executions.tenant_id" in sql


@pytest.mark.asyncio
async def test_checkpoint_latest_keeps_legacy_unscoped_call_explicitly_optional():
    db = AsyncMock()
    db.execute.return_value = type("Result", (), {"scalar_one_or_none": lambda self: None})()
    service = WorkflowExecutionCheckpointService(db)

    assert await service.latest(uuid4()) is None
    query = db.execute.call_args.args[0]
    assert "workflow_executions.tenant_id" not in str(query)
