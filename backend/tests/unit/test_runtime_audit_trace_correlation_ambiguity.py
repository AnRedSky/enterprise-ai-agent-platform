"""Regression tests for unambiguous Trace -> Workflow Execution resolution."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.runtime_operations.audit_trace_correlation import RuntimeAuditTraceCorrelationService


@pytest.mark.asyncio
async def test_historical_audit_resolves_repeated_trace_events_for_one_execution() -> None:
    tenant_id, execution_id = uuid4(), uuid4()
    audit = MagicMock(workflow_execution_id=None, trace_id="legacy-trace")
    result = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[execution_id])))
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    resolved = await RuntimeAuditTraceCorrelationService(db)._execution_id_from_audit(tenant_id, audit)

    assert resolved == execution_id
    statement = db.execute.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": False}))
    assert "DISTINCT" in compiled.upper()
    assert "workflow_trace_events.tenant_id" in compiled
    assert "workflow_trace_events.trace_id" in compiled


@pytest.mark.asyncio
async def test_historical_audit_rejects_ambiguous_trace_execution_mapping() -> None:
    tenant_id = uuid4()
    audit = MagicMock(workflow_execution_id=None, trace_id="ambiguous-trace")
    execution_a, execution_b = uuid4(), uuid4()
    result = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[execution_a, execution_b])))
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc_info:
        await RuntimeAuditTraceCorrelationService(db)._execution_id_from_audit(tenant_id, audit)

    assert exc_info.value.status_code == 409
    assert "multiple Workflow Executions" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_by_trace_rejects_ambiguous_trace_execution_mapping() -> None:
    tenant_id = uuid4()
    execution_a, execution_b = uuid4(), uuid4()
    result = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[execution_a, execution_b])))
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc_info:
        await RuntimeAuditTraceCorrelationService(db).by_trace(tenant_id, "ambiguous-trace")

    assert exc_info.value.status_code == 409
