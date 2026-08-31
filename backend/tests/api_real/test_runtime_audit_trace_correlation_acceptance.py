"""Phase 2.10-II Audit / Trace Correlation PostgreSQL acceptance。

测试验证 Execution → Trace / Audit / Operator Action 与反向深链，重点覆盖 tenant isolation、稳定分页与筛选。
不启动或停止任何服务，测试身份与业务事实全部自动创建并清理。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete

from app.infrastructure.db.session import SessionLocal
from app.models.audit import AuditLog
from app.models.core import Tenant, User
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.runtime_operations.audit_trace_correlation import RuntimeAuditTraceCorrelationService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_runtime_audit_trace_correlation_is_bidirectional_and_tenant_scoped() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    workflow_a, workflow_b = uuid.uuid4(), uuid.uuid4()
    version_a, version_b = uuid.uuid4(), uuid.uuid4()
    execution_a, execution_b = uuid.uuid4(), uuid.uuid4()
    trace_a, trace_b = uuid.uuid4(), uuid.uuid4()
    audit_a, audit_b = uuid.uuid4(), uuid.uuid4()
    action_a, action_b = uuid.uuid4(), uuid.uuid4()
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-correlation-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-correlation-b-{suffix}", status="active"),
                User(id=user_a, username=f"phase-210-correlation-a-{suffix}", password_hash="fixture", tenant_id=tenant_a, status="active"),
                User(id=user_b, username=f"phase-210-correlation-b-{suffix}", password_hash="fixture", tenant_id=tenant_b, status="active"),
                Workflow(id=workflow_a, name=f"correlation-a-{suffix}", description="", owner_id=user_a, tenant_id=tenant_a, status="published"),
                Workflow(id=workflow_b, name=f"correlation-b-{suffix}", description="", owner_id=user_b, tenant_id=tenant_b, status="published"),
                WorkflowVersion(id=version_a, workflow_id=workflow_a, version="1", definition={}, status="published", created_by=user_a),
                WorkflowVersion(id=version_b, workflow_id=workflow_b, version="1", definition={}, status="published", created_by=user_b),
                WorkflowExecution(id=execution_a, tenant_id=tenant_a, workflow_id=workflow_a, workflow_version_id=version_a, created_by=user_a, status="failed", error_code="FIXTURE_FAILURE", created_at=now),
                WorkflowExecution(id=execution_b, tenant_id=tenant_b, workflow_id=workflow_b, workflow_version_id=version_b, created_by=user_b, status="completed", created_at=now),
                WorkflowTraceEvent(id=trace_a, tenant_id=tenant_a, execution_id=execution_a, workflow_id=workflow_a, workflow_version_id=version_a, event_type="execution.state_changed", status="failed", trace_id=str(execution_a), actor_id=user_a, data={"fixture": suffix}, created_at=now),
                WorkflowTraceEvent(id=trace_b, tenant_id=tenant_b, execution_id=execution_b, workflow_id=workflow_b, workflow_version_id=version_b, event_type="execution.state_changed", status="completed", trace_id=str(execution_b), actor_id=user_b, data={"fixture": suffix}, created_at=now),
                AuditLog(id=audit_a, actor_id=user_a, tenant_id=tenant_a, workflow_id=workflow_a, workflow_version_id=version_a, workflow_execution_id=execution_a, action="operator.workflow_execution.retry", resource_type="workflow_execution", resource_id=str(execution_a), trace_id=str(execution_a), status="success", metadata_json={"fixture": suffix}, created_at=now),
                AuditLog(id=audit_b, actor_id=user_b, tenant_id=tenant_b, workflow_id=workflow_b, workflow_version_id=version_b, workflow_execution_id=execution_b, action="operator.workflow_execution.run", resource_type="workflow_execution", resource_id=str(execution_b), trace_id=str(execution_b), status="success", metadata_json={"fixture": suffix}, created_at=now),
                OperatorActionIdempotency(id=action_a, tenant_id=tenant_a, actor_id=user_a, resource_type="workflow_execution", resource_id=execution_a, action="retry", idempotency_key=f"correlation-a-{suffix}", status="succeeded", result_resource_id=execution_a, metadata_json={"fixture": suffix}, created_at=now, updated_at=now),
                OperatorActionIdempotency(id=action_b, tenant_id=tenant_b, actor_id=user_b, resource_type="workflow_execution", resource_id=execution_b, action="run", idempotency_key=f"correlation-b-{suffix}", status="succeeded", result_resource_id=execution_b, metadata_json={"fixture": suffix}, created_at=now, updated_at=now),
            ])
            await db.commit()

        async with SessionLocal() as db:
            service = RuntimeAuditTraceCorrelationService(db)
            result = await service.by_execution(tenant_a, execution_a)
            assert result is not None
            assert result["execution"].id == execution_a
            assert [item.id for item in result["traces"]["items"]] == [trace_a]
            assert [item.id for item in result["audits"]["items"]] == [audit_a]
            assert [item.id for item in result["operator_actions"]] == [action_a]

            filtered = await service.by_execution(
                tenant_a,
                execution_a,
                trace_event_type="execution.state_changed",
                audit_action="operator.workflow_execution.retry",
                trace_status="failed",
                audit_status="success",
            )
            assert filtered is not None
            assert filtered["traces"]["total"] == 1
            assert filtered["audits"]["total"] == 1

            rejected_filter = await service.by_execution(
                tenant_a,
                execution_a,
                trace_event_type="not-present",
                audit_action="operator.workflow_execution.run",
            )
            assert rejected_filter is not None
            assert rejected_filter["traces"]["total"] == 0
            assert rejected_filter["audits"]["total"] == 0

            reverse_trace = await service.by_trace(tenant_a, str(execution_a))
            assert reverse_trace is not None
            assert reverse_trace["execution"].id == execution_a

            reverse_audit = await service.by_audit(tenant_a, audit_a)
            assert reverse_audit is not None
            assert reverse_audit["execution"].id == execution_a
            assert reverse_audit["focus_audit_id"] == audit_a

            reverse_action = await service.by_operator_action(tenant_a, action_a)
            assert reverse_action is not None
            assert reverse_action["execution"].id == execution_a
            assert reverse_action["focus_operator_action_id"] == action_a

            assert await service.by_execution(tenant_a, execution_b) is None
            assert await service.by_audit(tenant_a, audit_b) is None
            assert await service.by_operator_action(tenant_a, action_b) is None
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(AuditLog).where(AuditLog.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WorkflowExecution).where(WorkflowExecution.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WorkflowVersion).where(WorkflowVersion.workflow_id.in_([workflow_a, workflow_b])))
            await db.execute(delete(Workflow).where(Workflow.id.in_([workflow_a, workflow_b])))
            await db.execute(delete(User).where(User.id.in_([user_a, user_b])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()
