from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.resume_contract import WorkflowExecutionResumeContractService


@pytest.mark.asyncio
async def test_resume_contract_reads_checkpoint_with_locked_execution_tenant_scope():
    tenant_id = uuid4()
    execution_id = uuid4()
    version_id = uuid4()
    checkpoint = SimpleNamespace(
        id=uuid4(), execution_id=execution_id, sequence=3, checkpoint_reason="frontier_completed",
        execution_status="running", node_status=None, node_id=None,
        state_data={}, input_data={}, output_data={},
    )
    execution = SimpleNamespace(
        id=execution_id, tenant_id=tenant_id, workflow_version_id=version_id,
        status="failed", worker_owner=None,
    )

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        SimpleNamespace(scalar_one_or_none=lambda: checkpoint),
        SimpleNamespace(scalar_one_or_none=lambda: None),
    ])
    service = WorkflowExecutionResumeContractService(db)
    execution_service = AsyncMock()
    execution_service._lock_execution = AsyncMock(return_value=execution)
    execution_service.resume_from_latest_checkpoint = AsyncMock(return_value=execution)

    import app.services.workflow.execution as execution_module
    original = execution_module.WorkflowExecutionService
    execution_module.WorkflowExecutionService = lambda db: execution_service
    try:
        result = await service.resume_with_outcome(execution, uuid4())
    finally:
        execution_module.WorkflowExecutionService = original

    assert result.outcome == "created"
    checkpoint_query = db.execute.call_args_list[0].args[0]
    sql = str(checkpoint_query)
    assert "workflow_execution_checkpoints.execution_id" in sql
    assert "workflow_executions.tenant_id" in sql
    execution_service.resume_from_latest_checkpoint.assert_awaited_once()
