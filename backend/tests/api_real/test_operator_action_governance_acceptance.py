"""Phase 2.10-II Operator Action Governance 的真实 PostgreSQL 验收。

职责：验证 Operator Action 的 tenant boundary、状态可用性、确认约束与幂等持久化事实。
边界：不启动任何服务、不调用真实 Provider；测试身份、Workflow、Execution、Trigger 与幂等数据均由用例自动创建和清理。
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import delete

from app.infrastructure.db.session import SessionLocal
from app.models.core import Tenant, User
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trigger import WorkflowTrigger
from app.services.runtime_operations import OperatorActionGovernanceService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_operator_action_governance_is_tenant_scoped_and_state_driven():
    """验证 Execution / Trigger Operator Action Contract 不允许跨租户访问并严格按状态计算。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    workflow_a, workflow_b = uuid.uuid4(), uuid.uuid4()
    version_a, version_b = uuid.uuid4(), uuid.uuid4()
    execution_a, execution_b = uuid.uuid4(), uuid.uuid4()
    trigger_a, trigger_b = uuid.uuid4(), uuid.uuid4()
    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-ii-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-ii-b-{suffix}", status="active"),
                User(id=user_a, username=f"phase-210-ii-user-a-{suffix}", password_hash="test", tenant_id=tenant_a),
                User(id=user_b, username=f"phase-210-ii-user-b-{suffix}", password_hash="test", tenant_id=tenant_b),
                Workflow(id=workflow_a, tenant_id=tenant_a, owner_id=user_a, name=f"workflow-a-{suffix}"),
                Workflow(id=workflow_b, tenant_id=tenant_b, owner_id=user_b, name=f"workflow-b-{suffix}"),
                WorkflowVersion(id=version_a, workflow_id=workflow_a, version="1.0.0", created_by=user_a, definition={}, status="draft"),
                WorkflowVersion(id=version_b, workflow_id=workflow_b, version="1.0.0", created_by=user_b, definition={}, status="draft"),
                WorkflowExecution(id=execution_a, tenant_id=tenant_a, workflow_id=workflow_a, workflow_version_id=version_a, created_by=user_a, status="pending", input_data={}),
                WorkflowExecution(id=execution_b, tenant_id=tenant_b, workflow_id=workflow_b, workflow_version_id=version_b, created_by=user_b, status="failed", input_data={}),
                WorkflowTrigger(id=trigger_a, tenant_id=tenant_a, workflow_id=workflow_a, created_by=user_a, name=f"trigger-a-{suffix}", trigger_type="manual", status="enabled", config={}),
                WorkflowTrigger(id=trigger_b, tenant_id=tenant_b, workflow_id=workflow_b, created_by=user_b, name=f"trigger-b-{suffix}", trigger_type="manual", status="disabled", config={}),
            ])
            await db.commit()

        async with SessionLocal() as db:
            service = OperatorActionGovernanceService(db)
            execution_contract = await service.execution_availability(execution_a, tenant_a, user_a, False)
            action_map = {item["action"]: item for item in execution_contract["actions"]}
            assert action_map["run"]["allowed"] is True
            assert action_map["cancel"]["allowed"] is True
            assert action_map["retry"]["allowed"] is False
            assert action_map["retry"]["requires_idempotency_key"] is True
            assert action_map["cancel"]["requires_confirmation"] is True

            trigger_contract = await service.trigger_availability(trigger_a, tenant_a, user_a, False)
            trigger_map = {item["action"]: item for item in trigger_contract["actions"]}
            assert trigger_map["disable"]["allowed"] is True
            assert trigger_map["enable"]["allowed"] is False
            assert trigger_map["invoke"]["allowed"] is True

            with pytest.raises(HTTPException) as execution_scope_error:
                await service.execution_availability(execution_a, tenant_b, user_b, False)
            assert execution_scope_error.value.status_code == 404

            with pytest.raises(HTTPException) as trigger_scope_error:
                await service.trigger_availability(trigger_a, tenant_b, user_b, False)
            assert trigger_scope_error.value.status_code == 404

            first = await service._claim_idempotency(
                tenant_id=tenant_a, actor_id=user_a, resource_type="workflow_execution",
                resource_id=execution_a, action="retry", idempotency_key=f"retry-{suffix}",
            )
            assert first is None
            await db.commit()

        async with SessionLocal() as db:
            service = OperatorActionGovernanceService(db)
            existing = await service._claim_idempotency(
                tenant_id=tenant_a, actor_id=user_a, resource_type="workflow_execution",
                resource_id=execution_a, action="retry", idempotency_key=f"retry-{suffix}",
            )
            assert existing is not None
            assert existing.status == "started"
            assert existing.tenant_id == tenant_a

            other_tenant = await service._claim_idempotency(
                tenant_id=tenant_b, actor_id=user_b, resource_type="workflow_execution",
                resource_id=execution_b, action="retry", idempotency_key=f"retry-{suffix}",
            )
            assert other_tenant is None
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WorkflowTrigger).where(WorkflowTrigger.id.in_([trigger_a, trigger_b])))
            await db.execute(delete(WorkflowExecution).where(WorkflowExecution.id.in_([execution_a, execution_b])))
            await db.execute(delete(WorkflowVersion).where(WorkflowVersion.id.in_([version_a, version_b])))
            await db.execute(delete(Workflow).where(Workflow.id.in_([workflow_a, workflow_b])))
            await db.execute(delete(User).where(User.id.in_([user_a, user_b])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()
