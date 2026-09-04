"""Operator Trigger 生命周期 PostgreSQL 集成测试。

职责：使用真实 PostgreSQL 验证 Trigger enable/disable/delete 的状态边界、租户隔离与治理事务原子性。
边界：不覆盖 HTTP API，不启动任何服务；不复制 Trigger 状态机实现，只调用正式 Operator Governance 与 Trigger Service。
关键依赖：真实 PostgreSQL、Workflow/WorkflowTrigger ORM、OperatorActionGovernanceService、WorkflowTriggerService。
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.infrastructure.db import SessionLocal
from app.infrastructure.db.session import engine
from app.models.core import AuditLog, Tenant, User
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_trigger import WorkflowTrigger
from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService
from app.services.trigger import WorkflowTriggerService


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_database_integration() -> None:
    """真实 PostgreSQL 测试必须由显式 Gate 开启，避免普通回归隐式依赖数据库。"""
    if os.getenv("RUN_DATABASE_INTEGRATION") != "1":
        pytest.skip("需要设置 RUN_DATABASE_INTEGRATION=1 才执行 Trigger Lifecycle PostgreSQL 验收")


@pytest_asyncio.fixture(autouse=True)
async def reset_database_engine_pool() -> None:
    """隔离 pytest-asyncio 事件循环，避免 asyncpg 连接跨测试循环复用。"""
    await engine.dispose()
    try:
        yield
    finally:
        await engine.dispose()


async def _create_fixture(tenant_id, user_id, *, trigger_status: str = "disabled"):
    """创建最小 Workflow、Published Version 与 Trigger 前置事实。"""
    workflow_id = uuid4()
    version_id = uuid4()
    trigger_id = uuid4()
    async with SessionLocal() as session:
        async with session.begin():
            session.add(Tenant(id=tenant_id, name=f"trigger-lifecycle-{tenant_id}"))
            session.add(User(
                id=user_id,
                username=f"trigger-lifecycle-{user_id}",
                password_hash="integration-test",
                tenant_id=tenant_id,
            ))
            workflow = Workflow(
                id=workflow_id,
                name=f"trigger-lifecycle-{workflow_id}",
                owner_id=user_id,
                tenant_id=tenant_id,
                status="published",
                published_version_id=None,
            )
            session.add(workflow)
            await session.flush()
            version = WorkflowVersion(
                id=version_id,
                workflow_id=workflow_id,
                version="1",
                definition={
                    "config": {},
                    "nodes": [{"id": "input", "type": "input", "config": {}}],
                    "edges": [],
                },
                status="published",
                created_by=user_id,
            )
            session.add(version)
            await session.flush()
            workflow.published_version_id = version_id
            session.add(WorkflowTrigger(
                id=trigger_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                name=f"manual-{trigger_id}",
                trigger_type="manual",
                status=trigger_status,
                created_by=user_id,
                config={},
            ))
            await session.flush()
    return workflow_id, version_id, trigger_id


async def _cleanup(*tenant_ids, user_ids) -> None:
    """清理本测试生成的 Trigger、审计、幂等事实、Workflow 与身份。"""
    async with SessionLocal() as session:
        await session.execute(delete(AuditLog).where(AuditLog.tenant_id.in_(tenant_ids)))
        await session.execute(delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id.in_(tenant_ids)))
        await session.execute(delete(WorkflowTrigger).where(WorkflowTrigger.tenant_id.in_(tenant_ids)))
        await session.execute(delete(WorkflowVersion).where(WorkflowVersion.created_by.in_(user_ids)))
        await session.execute(delete(Workflow).where(Workflow.owner_id.in_(user_ids)))
        await session.execute(delete(User).where(User.id.in_(user_ids)))
        await session.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))
        await session.commit()


@pytest.mark.asyncio
async def test_operator_trigger_enable_disable_persists_state_and_operator_audit() -> None:
    """验证 Enable/Disable 复用正式 Trigger Service，并分别持久化治理审计事实。"""
    tenant_id = uuid4()
    user_id = uuid4()
    _, _, trigger_id = await _create_fixture(tenant_id, user_id, trigger_status="disabled")
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            enabled = await service.execute_trigger(
                trigger_id, tenant_id, user_id, True, "enable", confirm=True,
            )
            assert enabled.status == "enabled"

        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            disabled = await service.execute_trigger(
                trigger_id, tenant_id, user_id, True, "disable", confirm=True,
            )
            assert disabled.status == "disabled"

        async with SessionLocal() as session:
            audits = (await session.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.resource_id == str(trigger_id),
            ))).scalars().all()
            actions = {audit.action for audit in audits}
            assert "operator.workflow_trigger.enable" in actions
            assert "operator.workflow_trigger.disable" in actions
            assert len(audits) == 2
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])


@pytest.mark.asyncio
async def test_operator_trigger_lifecycle_rejects_invalid_state_without_audit() -> None:
    """验证状态机不允许重复 Enable/Disable，非法请求不会写入 Operator Audit。"""
    tenant_id = uuid4()
    user_id = uuid4()
    _, _, trigger_id = await _create_fixture(tenant_id, user_id, trigger_status="enabled")
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            with pytest.raises(HTTPException) as exc_info:
                await service.execute_trigger(
                    trigger_id, tenant_id, user_id, True, "enable", confirm=True,
                )
            assert exc_info.value.status_code == 409

        async with SessionLocal() as session:
            assert (await session.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.resource_id == str(trigger_id),
                AuditLog.action == "operator.workflow_trigger.enable",
            ))).scalars().all() == []
            trigger = (await session.execute(select(WorkflowTrigger).where(
                WorkflowTrigger.id == trigger_id,
                WorkflowTrigger.tenant_id == tenant_id,
            ))).scalar_one()
            assert trigger.status == "enabled"
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])


@pytest.mark.asyncio
async def test_operator_trigger_delete_is_atomic_with_operator_audit() -> None:
    """验证 Delete 与 Operator Audit 共用同一事务，成功时 Trigger 删除且审计事实落库。"""
    tenant_id = uuid4()
    user_id = uuid4()
    _, _, trigger_id = await _create_fixture(tenant_id, user_id, trigger_status="disabled")
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            deleted = await service.execute_trigger(
                trigger_id, tenant_id, user_id, True, "delete", confirm=True,
            )
            assert deleted.id == trigger_id

        async with SessionLocal() as session:
            trigger = (await session.execute(select(WorkflowTrigger).where(
                WorkflowTrigger.id == trigger_id,
                WorkflowTrigger.tenant_id == tenant_id,
            ))).scalar_one_or_none()
            audit = (await session.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.resource_id == str(trigger_id),
                AuditLog.action == "operator.workflow_trigger.delete",
            ))).scalar_one_or_none()
            assert trigger is None
            assert audit is not None
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])


@pytest.mark.asyncio
async def test_operator_trigger_lifecycle_rolls_back_state_when_final_audit_fails() -> None:
    """验证 Trigger 状态变更后最终审计失败时，状态、审计与幂等事实全部回滚。"""
    tenant_id = uuid4()
    user_id = uuid4()
    _, _, trigger_id = await _create_fixture(tenant_id, user_id, trigger_status="disabled")
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            service._audit = AsyncMock(side_effect=RuntimeError("operator audit failure"))
            with pytest.raises(RuntimeError, match="operator audit failure"):
                await service.execute_trigger(
                    trigger_id, tenant_id, user_id, True, "enable", confirm=True,
                )

        async with SessionLocal() as session:
            trigger = (await session.execute(select(WorkflowTrigger).where(
                WorkflowTrigger.id == trigger_id,
                WorkflowTrigger.tenant_id == tenant_id,
            ))).scalar_one()
            audits = (await session.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.resource_id == str(trigger_id),
                AuditLog.action == "operator.workflow_trigger.enable",
            ))).scalars().all()
            idempotency = (await session.execute(select(OperatorActionIdempotency).where(
                OperatorActionIdempotency.tenant_id == tenant_id,
            ))).scalars().all()
            assert trigger.status == "disabled"
            assert audits == []
            assert idempotency == []
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])
