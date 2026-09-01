"""Runtime Operator Action 审计查询真实 PostgreSQL 验收。

职责：验证 Operator Action 审计查询使用 AuditLog 唯一事实源、租户隔离、精确过滤与稳定分页。
边界：不启动任何服务；测试租户、用户、Workflow、Execution 和 AuditLog 均由用例自动创建并清理。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from app.infrastructure.db.session import SessionLocal
from app.models.core import AuditLog, Tenant, User
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.services.runtime_operations import OperatorAuditQueryService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_operator_audit_query_is_canonical_tenant_scoped_and_filterable() -> None:
    """验证 Operator Action 审计只来自 AuditLog，并且所有查询条件保持租户边界。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    workflow_a, workflow_b = uuid.uuid4(), uuid.uuid4()
    version_a, version_b = uuid.uuid4(), uuid.uuid4()
    execution_a, execution_b = uuid.uuid4(), uuid.uuid4()
    audit_a, audit_b, non_operator = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-operator-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-operator-b-{suffix}", status="active"),
                User(id=user_a, username=f"phase-210-operator-a-{suffix}", password_hash="fixture", tenant_id=tenant_a, status="active"),
                User(id=user_b, username=f"phase-210-operator-b-{suffix}", password_hash="fixture", tenant_id=tenant_b, status="active"),
                Workflow(id=workflow_a, tenant_id=tenant_a, owner_id=user_a, name=f"operator-a-{suffix}"),
                Workflow(id=workflow_b, tenant_id=tenant_b, owner_id=user_b, name=f"operator-b-{suffix}"),
                WorkflowVersion(id=version_a, workflow_id=workflow_a, version="1", created_by=user_a, definition={}, status="draft"),
                WorkflowVersion(id=version_b, workflow_id=workflow_b, version="1", created_by=user_b, definition={}, status="draft"),
                WorkflowExecution(id=execution_a, tenant_id=tenant_a, workflow_id=workflow_a, workflow_version_id=version_a, created_by=user_a, status="failed", input_data={}),
                WorkflowExecution(id=execution_b, tenant_id=tenant_b, workflow_id=workflow_b, workflow_version_id=version_b, created_by=user_b, status="failed", input_data={}),
                AuditLog(id=audit_a, actor_id=user_a, tenant_id=tenant_a, workflow_id=workflow_a, workflow_version_id=version_a, workflow_execution_id=execution_a, action="operator.workflow_execution.retry", resource_type="workflow_execution", resource_id=str(execution_a), trace_id=str(execution_a), status="success", metadata_json={"fixture": suffix}, created_at=now - timedelta(minutes=2)),
                AuditLog(id=audit_b, actor_id=user_b, tenant_id=tenant_b, workflow_id=workflow_b, workflow_version_id=version_b, workflow_execution_id=execution_b, action="operator.workflow_execution.retry", resource_type="workflow_execution", resource_id=str(execution_b), trace_id=str(execution_b), status="success", metadata_json={"fixture": suffix}, created_at=now - timedelta(minutes=1)),
                AuditLog(id=non_operator, actor_id=user_a, tenant_id=tenant_a, workflow_id=workflow_a, workflow_version_id=version_a, workflow_execution_id=execution_a, action="workflow.execution.read", resource_type="workflow_execution", resource_id=str(execution_a), trace_id=str(execution_a), status="success", metadata_json={"fixture": suffix}, created_at=now),
            ])
            await db.commit()

        async with SessionLocal() as db:
            service = OperatorAuditQueryService(db)
            result = await service.query(tenant_a, page=1, page_size=10)
            assert result["total"] == 1
            assert [item.id for item in result["items"]] == [audit_a]

            filtered = await service.query(
                tenant_a,
                page=1,
                page_size=1,
                action="operator.workflow_execution.retry",
                actor_id=user_a,
                workflow_execution_id=execution_a,
                trace_id=str(execution_a),
                status="success",
                since=now - timedelta(minutes=5),
                until=now + timedelta(minutes=1),
            )
            assert filtered["total"] == 1
            assert filtered["items"][0].id == audit_a
            assert filtered["page"] == 1
            assert filtered["page_size"] == 1

            other_tenant = await service.query(
                tenant_a,
                action="operator.workflow_execution.retry",
                actor_id=user_b,
            )
            assert other_tenant["total"] == 0

            with pytest.raises(ValueError, match="action must start with operator"):
                await service.query(tenant_a, action="workflow.execution.read")

            with pytest.raises(ValueError, match="since must not be later than until"):
                await service.query(tenant_a, since=now, until=now - timedelta(seconds=1))
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(AuditLog).where(AuditLog.id.in_([audit_a, audit_b, non_operator])))
            await db.execute(delete(WorkflowExecution).where(WorkflowExecution.id.in_([execution_a, execution_b])))
            await db.execute(delete(WorkflowVersion).where(WorkflowVersion.id.in_([version_a, version_b])))
            await db.execute(delete(Workflow).where(Workflow.id.in_([workflow_a, workflow_b])))
            await db.execute(delete(User).where(User.id.in_([user_a, user_b])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()
