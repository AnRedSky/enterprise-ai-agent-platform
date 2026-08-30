"""Phase 2.10-II Operator Action 执行真实验收。

职责：验证 Trigger Operator Action 真正委托现有 Trigger Domain Service，并记录 tenant-scoped Operational Audit。
边界：不启动任何服务、不调用外部 Provider；测试数据由用例自动创建和清理。
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.infrastructure.db.session import SessionLocal
from app.models.core import AuditLog, Tenant, User
from app.models.workflow import Workflow
from app.models.workflow_trigger import WorkflowTrigger
from app.services.runtime_operations import OperatorActionGovernanceService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_operator_trigger_actions_reuse_domain_service_and_write_audit():
    """验证 Enable / Disable 使用现有 Trigger Service，并保持租户隔离与高风险确认。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    workflow_a, workflow_b = uuid.uuid4(), uuid.uuid4()
    trigger_a, trigger_b = uuid.uuid4(), uuid.uuid4()
    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-ii-exec-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-ii-exec-b-{suffix}", status="active"),
                User(id=user_a, username=f"phase-210-ii-exec-user-a-{suffix}", password_hash="test", tenant_id=tenant_a),
                User(id=user_b, username=f"phase-210-ii-exec-user-b-{suffix}", password_hash="test", tenant_id=tenant_b),
                Workflow(id=workflow_a, tenant_id=tenant_a, owner_id=user_a, name=f"workflow-a-{suffix}"),
                Workflow(id=workflow_b, tenant_id=tenant_b, owner_id=user_b, name=f"workflow-b-{suffix}"),
                WorkflowTrigger(id=trigger_a, tenant_id=tenant_a, workflow_id=workflow_a, created_by=user_a,
                                name=f"trigger-a-{suffix}", trigger_type="manual", status="disabled", config={}),
                WorkflowTrigger(id=trigger_b, tenant_id=tenant_b, workflow_id=workflow_b, created_by=user_b,
                                name=f"trigger-b-{suffix}", trigger_type="manual", status="enabled", config={}),
            ])
            await db.commit()

        async with SessionLocal() as db:
            service = OperatorActionGovernanceService(db)
            with pytest.raises(HTTPException) as confirmation_error:
                await service.execute_trigger(trigger_a, tenant_a, user_a, False, "enable", confirm=False)
            assert confirmation_error.value.status_code == 400

            enabled = await service.execute_trigger(trigger_a, tenant_a, user_a, False, "enable", confirm=True)
            assert enabled.id == trigger_a
            assert enabled.status == "enabled"

            disabled = await service.execute_trigger(trigger_a, tenant_a, user_a, False, "disable", confirm=True)
            assert disabled.id == trigger_a
            assert disabled.status == "disabled"

            with pytest.raises(HTTPException) as scope_error:
                await service.execute_trigger(trigger_a, tenant_b, user_b, False, "enable", confirm=True)
            assert scope_error.value.status_code == 404

            audits = (await db.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_a,
                AuditLog.resource_id == str(trigger_a),
                AuditLog.action.in_(["operator.workflow_trigger.enable", "operator.workflow_trigger.disable"]),
            ))).scalars().all()
            assert {item.action for item in audits} == {
                "operator.workflow_trigger.enable",
                "operator.workflow_trigger.disable",
            }
            assert all(item.status == "success" for item in audits)
            assert all(item.tenant_id == tenant_a for item in audits)
            assert await db.scalar(select(AuditLog.id).where(
                AuditLog.tenant_id == tenant_b,
                AuditLog.resource_id == str(trigger_a),
            )) is None
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(AuditLog).where(AuditLog.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WorkflowTrigger).where(WorkflowTrigger.id.in_([trigger_a, trigger_b])))
            await db.execute(delete(Workflow).where(Workflow.id.in_([workflow_a, workflow_b])))
            await db.execute(delete(User).where(User.id.in_([user_a, user_b])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()
