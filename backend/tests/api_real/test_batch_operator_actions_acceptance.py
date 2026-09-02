"""Phase 2.10-II Controlled Batch Operations 的真实 PostgreSQL 验收。

职责：验证批量 Operator Action 的 tenant boundary、逐项结果和现有生命周期委托。
边界：不启动服务、不调用真实 Provider；测试身份与业务事实均由用例自动创建和清理。
关键约束：Operator Action 可能产生 Integration Event，清理租户前必须先删除事件事实。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select

from app.infrastructure.db.session import SessionLocal
from app.models.core import AuditLog, Tenant, User
from app.models.integration_event import IntegrationEventRecord
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.services.runtime_operations.batch_operator_actions import BatchOperatorActionService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_batch_operator_action_is_tenant_scoped_and_partially_completable():
    """验证同一批次中跨租户资源不会越权，并且合法项目仍可继续完成。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    workflow_a, workflow_b = uuid.uuid4(), uuid.uuid4()
    version_a, version_b = uuid.uuid4(), uuid.uuid4()
    execution_a, execution_b = uuid.uuid4(), uuid.uuid4()
    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-batch-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-batch-b-{suffix}", status="active"),
                User(id=user_a, username=f"phase-210-batch-user-a-{suffix}", password_hash="test", tenant_id=tenant_a),
                User(id=user_b, username=f"phase-210-batch-user-b-{suffix}", password_hash="test", tenant_id=tenant_b),
                Workflow(id=workflow_a, tenant_id=tenant_a, owner_id=user_a, name=f"batch-workflow-a-{suffix}"),
                Workflow(id=workflow_b, tenant_id=tenant_b, owner_id=user_b, name=f"batch-workflow-b-{suffix}"),
                WorkflowVersion(id=version_a, workflow_id=workflow_a, version="1.0.0", created_by=user_a, definition={}, status="draft"),
                WorkflowVersion(id=version_b, workflow_id=workflow_b, version="1.0.0", created_by=user_b, definition={}, status="draft"),
                WorkflowExecution(id=execution_a, tenant_id=tenant_a, workflow_id=workflow_a, workflow_version_id=version_a, created_by=user_a, status="pending", input_data={}),
                WorkflowExecution(id=execution_b, tenant_id=tenant_b, workflow_id=workflow_b, workflow_version_id=version_b, created_by=user_b, status="pending", input_data={}),
            ])
            await db.commit()

        async with SessionLocal() as db:
            result = await BatchOperatorActionService(db).execute(
                resource_type="workflow_execution",
                action="cancel",
                resource_ids=[execution_a, execution_b],
                tenant_id=tenant_a,
                actor_id=user_a,
                is_admin=True,
                confirm=True,
                reason="phase-2.10 batch acceptance",
            )
            assert result["total"] == 2
            assert result["succeeded_count"] == 1
            assert result["rejected_count"] == 1
            assert result["failed_count"] == 0
            assert result["items"][0].resource_id == execution_a
            assert result["items"][0].status == "succeeded"
            assert result["items"][1].resource_id == execution_b
            assert result["items"][1].status == "rejected"
            assert result["items"][1].error_code == "HTTP_404"

        async with SessionLocal() as db:
            state_a = (await db.execute(select(WorkflowExecution.status).where(WorkflowExecution.id == execution_a))).scalar_one()
            state_b = (await db.execute(select(WorkflowExecution.status).where(WorkflowExecution.id == execution_b))).scalar_one()
            assert state_a == "cancelled"
            assert state_b == "pending"
    finally:
        async with SessionLocal() as db:
            # Workflow Execution 的取消动作会产生 Durable Integration Event；事件是租户的父事实，
            # 删除租户前必须显式清理它。Webhook Delivery 对事件使用 ON DELETE CASCADE，会随事件一并删除。
            await db.execute(
                delete(IntegrationEventRecord).where(
                    IntegrationEventRecord.tenant_id.in_([tenant_a, tenant_b])
                )
            )
            await db.execute(delete(AuditLog).where(AuditLog.workflow_execution_id.in_([execution_a, execution_b])))
            # Operator Action 的 actor_id 是 users 的 RESTRICT 外键，必须在删除用户前清理幂等事实。
            await db.execute(delete(OperatorActionIdempotency).where(
                OperatorActionIdempotency.actor_id.in_([user_a, user_b])
            ))
            await db.execute(delete(WorkflowExecution).where(WorkflowExecution.id.in_([execution_a, execution_b])))
            await db.execute(delete(WorkflowVersion).where(WorkflowVersion.id.in_([version_a, version_b])))
            await db.execute(delete(Workflow).where(Workflow.id.in_([workflow_a, workflow_b])))
            await db.execute(delete(User).where(User.id.in_([user_a, user_b])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()
