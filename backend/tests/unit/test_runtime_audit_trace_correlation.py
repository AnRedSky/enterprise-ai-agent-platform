"""Runtime Audit / Trace 关联服务单元测试。

覆盖分页边界、Execution 正向关联、Trace/Audit/Operator Action 反向定位及结果 Execution 关联。
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.runtime_operations.audit_trace_correlation import RuntimeAuditTraceCorrelationService


def test_correlation_page_is_stable_and_bounded() -> None:
    assert RuntimeAuditTraceCorrelationService._page(0, 500) == (1, 100, 0)
    assert RuntimeAuditTraceCorrelationService._page(3, 20) == (3, 20, 40)


@pytest.mark.asyncio
async def test_by_execution_returns_trace_audit_and_operator_facts() -> None:
    tenant_id, execution_id = uuid4(), uuid4()
    execution = MagicMock(id=execution_id, tenant_id=tenant_id)
    trace = MagicMock()
    audit = MagicMock()
    action = MagicMock()

    def page_result(items, total):
        result = MagicMock()
        result.scalar_one.return_value = total
        result.scalars.return_value.all.return_value = items
        return result

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=execution)),
        page_result([], 0),
        page_result([trace], 1),
        page_result([], 0),
        page_result([audit], 1),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[action])))),
    ])

    result = await RuntimeAuditTraceCorrelationService(db).by_execution(tenant_id, execution_id)

    assert result["execution"] is execution
    assert result["traces"]["items"] == [trace]
    assert result["audits"]["items"] == [audit]
    assert result["operator_actions"] == [action]


@pytest.mark.asyncio
async def test_by_operator_action_without_execution_keeps_action_only() -> None:
    tenant_id, action_id = uuid4(), uuid4()
    action = MagicMock(id=action_id, result_resource_id=None, resource_type="workflow_trigger", resource_id=uuid4())
    action_result = MagicMock(scalar_one_or_none=MagicMock(return_value=action))
    db = MagicMock()
    db.execute = AsyncMock(return_value=action_result)

    result = await RuntimeAuditTraceCorrelationService(db).by_operator_action(tenant_id, action_id)

    assert result["execution"] is None
    assert result["operator_actions"] == [action]
    assert result["traces"]["total"] == 0
    assert result["audits"]["total"] == 0


@pytest.mark.asyncio
async def test_by_trace_returns_none_for_unknown_tenant_scoped_trace() -> None:
    db = MagicMock()
    trace_result = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    db.execute = AsyncMock(return_value=trace_result)

    result = await RuntimeAuditTraceCorrelationService(db).by_trace(uuid4(), "missing-trace")

    assert result is None
