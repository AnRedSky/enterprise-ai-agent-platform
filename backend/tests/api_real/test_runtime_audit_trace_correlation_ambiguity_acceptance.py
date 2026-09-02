"""Real PostgreSQL acceptance for deterministic Trace -> Execution correlation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete

from app.infrastructure.db.session import SessionLocal
from app.models.audit import AuditLog
from app.models.core import Tenant, User
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.runtime_operations.audit_trace_correlation import RuntimeAuditTraceCorrelationService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_repeated_trace_events_do_not_break_historical_audit_resolution() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    workflow_id, version_id, execution_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    trace_event_a, trace_event_b, audit_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    trace_id = f"legacy-repeated-{suffix}"
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_id, name=f"trace-ambiguity-{suffix}", status="active"),
                User(id=user_id, username=f"trace-ambiguity-{suffix}", password_hash="fixture", tenant_id=tenant_id, status="active"),
                Workflow(id=workflow_id, name=f"trace-ambiguity-{suffix}", description="", owner_id=user_id, tenant_id=tenant_id, status="published"),
                WorkflowVersion(id=version_id, workflow_id=workflow_id, version="1", definition={}, status="published", created_by=user_id),
                WorkflowExecution(id=execution_id, tenant_id=tenant_id, workflow_id=workflow_id, workflow_version_id=version_id, created_by=user_id, status="failed", error_code="FIXTURE_FAILURE", created_at=now),
            ])
            await db.flush()
            db.add_all([
                WorkflowTraceEvent(id=trace_event_a, tenant_id=tenant_id, execution_id=execution_id, workflow_id=workflow_id, workflow_version_id=version_id, event_type="execution.state_changed", status="failed", trace_id=trace_id, actor_id=user_id, data={"fixture": "a"}, created_at=now),
                WorkflowTraceEvent(id=trace_event_b, tenant_id=tenant_id, execution_id=execution_id, workflow_id=workflow_id, workflow_version_id=version_id, event_type="execution.error", status="failed", trace_id=trace_id, actor_id=user_id, data={"fixture": "b"}, created_at=now),
                AuditLog(id=audit_id, actor_id=user_id, tenant_id=tenant_id, workflow_id=workflow_id, workflow_version_id=version_id, workflow_execution_id=None, action="legacy.workflow_execution.trace", resource_type="workflow_execution", resource_id=str(execution_id), trace_id=trace_id, status="success", metadata_json={"legacy": True}, created_at=now),
            ])
            await db.commit()

        async with SessionLocal() as db:
            service = RuntimeAuditTraceCorrelationService(db)
            reverse_audit = await service.by_audit(tenant_id, audit_id)
            assert reverse_audit is not None
            assert reverse_audit["execution"].id == execution_id

            reverse_trace = await service.by_trace(tenant_id, trace_id)
            assert reverse_trace is not None
            assert reverse_trace["execution"].id == execution_id
            assert reverse_trace["traces"]["total"] == 2
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(AuditLog).where(AuditLog.id == audit_id))
            await db.execute(delete(WorkflowTraceEvent).where(WorkflowTraceEvent.id.in_([trace_event_a, trace_event_b])))
            await db.execute(delete(WorkflowExecution).where(WorkflowExecution.id == execution_id))
            await db.execute(delete(WorkflowVersion).where(WorkflowVersion.id == version_id))
            await db.execute(delete(Workflow).where(Workflow.id == workflow_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()
