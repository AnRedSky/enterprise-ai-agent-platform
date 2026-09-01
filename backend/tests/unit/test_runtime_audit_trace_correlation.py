"""Runtime Audit / Trace 关联服务单元测试。

覆盖分页边界、Execution 正向关联、Trace/Audit/Operator Action 反向定位及历史审计兼容解析。
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
async def test_paged_audits_includes_legacy_audit_resolved_by_trace() -> None:
    tenant_id, execution_id = uuid4(), uuid4()
    audit = MagicMock()

    count_result = MagicMock(scalar_one=MagicMock(return_value=2))
    rows_result = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[audit, MagicMock()]))))
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    result = await RuntimeAuditTraceCorrelationService(db)._paged_audits(
        tenant_id,
        execution_id,
        page=1,
        page_size=50,
    )

    assert result["items"][0] is audit
    assert result["total"] == 2
    statement = db.execute.await_args_list[0].args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": False}))
    assert "audit_logs.tenant_id" in compiled
    assert "audit_logs.workflow_execution_id" in compiled
    assert "audit_logs.trace_id" in compiled
    assert "workflow_trace_events.execution_id" in compiled
    assert "workflow_trace_events.tenant_id" in compiled


@pytest.mark.asyncio
async def test_by_operator_action_without_execution_keeps_requested_page_size() -> None:
    tenant_id, action_id = uuid4(), uuid4()
    action = MagicMock(
        id=action_id,
        result_resource_type=None,
        result_resource_id=None,
        resource_type="workflow_trigger",
        resource_id=uuid4(),
    )
    action_result = MagicMock(scalar_one_or_none=MagicMock(return_value=action))
    db = MagicMock()
    db.execute = AsyncMock(return_value=action_result)

    result = await RuntimeAuditTraceCorrelationService(db).by_operator_action(
        tenant_id,
        action_id,
        trace_page=2,
        trace_page_size=20,
        audit_page=3,
        audit_page_size=30,
    )

    assert result["execution"] is None
    assert result["operator_actions"] == [action]
    assert result["traces"] == {"items": [], "page": 2, "page_size": 20, "total": 0}
    assert result["audits"] == {"items": [], "page": 3, "page_size": 30, "total": 0}


@pytest.mark.asyncio
async def test_by_operator_action_rejects_untyped_result_as_execution() -> None:
    tenant_id, action_id, result_id = uuid4(), uuid4(), uuid4()
    action = MagicMock(
        id=action_id,
        result_resource_type="workflow_trigger",
        result_resource_id=result_id,
        resource_type="workflow_trigger",
        resource_id=uuid4(),
    )
    action_result = MagicMock(scalar_one_or_none=MagicMock(return_value=action))
    db = MagicMock()
    db.execute = AsyncMock(return_value=action_result)

    result = await RuntimeAuditTraceCorrelationService(db).by_operator_action(tenant_id, action_id)

    assert result["execution"] is None
    assert result["operator_actions"] == [action]
    assert result["traces"]["total"] == 0
    assert result["audits"]["total"] == 0


@pytest.mark.asyncio
async def test_historical_audit_can_resolve_execution_from_tenant_scoped_trace() -> None:
    tenant_id, execution_id = uuid4(), uuid4()
    audit = MagicMock(workflow_execution_id=None, trace_id="legacy-trace")
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=execution_id))
    )

    result = await RuntimeAuditTraceCorrelationService(db)._execution_id_from_audit(tenant_id, audit)

    assert result == execution_id
    statement = db.execute.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": False}))
    assert "workflow_trace_events.tenant_id" in compiled
    assert "workflow_trace_events.trace_id" in compiled


@pytest.mark.asyncio
async def test_historical_audit_without_trace_id_cannot_guess_execution_mapping() -> None:
    audit = MagicMock(workflow_execution_id=None, trace_id=None)
    db = MagicMock()
    db.execute = AsyncMock()

    result = await RuntimeAuditTraceCorrelationService(db)._execution_id_from_audit(uuid4(), audit)

    assert result is None
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_by_trace_returns_none_for_unknown_tenant_scoped_trace() -> None:
    db = MagicMock()
    trace_result = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    db.execute = AsyncMock(return_value=trace_result)

    result = await RuntimeAuditTraceCorrelationService(db).by_trace(uuid4(), "missing-trace")

    assert result is None
