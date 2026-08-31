"""Operator Action 结果资源类型与失败结果清理单元测试。"""

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService


@pytest.mark.asyncio
async def test_finish_idempotency_persists_typed_workflow_execution_result() -> None:
    record = SimpleNamespace(
        tenant_id=uuid4(),
        idempotency_key="retry-1",
        status="started",
        result_resource_type=None,
        result_resource_id=None,
        error_code=None,
    )
    result = MagicMock(scalar_one=MagicMock(return_value=record))
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()

    service = OperatorActionGovernanceService(db)
    result_id = uuid4()
    await service._finish_idempotency(
        "retry-1",
        record.tenant_id,
        result_id,
        result_resource_type="workflow_execution",
    )

    assert record.status == "succeeded"
    assert record.result_resource_type == "workflow_execution"
    assert record.result_resource_id == result_id
    assert record.error_code is None
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_finish_idempotency_clears_result_for_failed_action() -> None:
    record = SimpleNamespace(
        tenant_id=uuid4(),
        idempotency_key="invoke-1",
        status="started",
        result_resource_type=None,
        result_resource_id=None,
        error_code=None,
    )
    result = MagicMock(scalar_one=MagicMock(return_value=record))
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()

    service = OperatorActionGovernanceService(db)
    await service._finish_idempotency(
        "invoke-1",
        record.tenant_id,
        uuid4(),
        result_resource_type="workflow_execution",
        status="failed",
        error_code="HTTP_409",
    )

    assert record.status == "failed"
    assert record.result_resource_type is None
    assert record.result_resource_id is None
    assert record.error_code == "HTTP_409"


@pytest.mark.asyncio
async def test_reuse_rejects_non_execution_result_type() -> None:
    record = SimpleNamespace(
        tenant_id=uuid4(),
        status="succeeded",
        result_resource_type="workflow_trigger",
        result_resource_id=uuid4(),
    )
    db = MagicMock()
    service = OperatorActionGovernanceService(db)

    with pytest.raises(HTTPException) as exc_info:
        await service._reuse_or_raise(record)

    assert exc_info.value.status_code == 409
    assert "Workflow Execution" in str(exc_info.value.detail)
