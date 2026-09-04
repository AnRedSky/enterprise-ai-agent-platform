"""Operator Execution Governance PostgreSQL 集成测试。

职责：使用真实 PostgreSQL 验证 Execution run/cancel 的状态持久化、非法状态保护与治理事务原子性。
边界：不启动任何服务，不复制 Workflow Execution 状态机；实际 run/cancel 领域执行在本测试中仅替换为最小状态变更，以聚焦治理事务边界。
关键依赖：真实 PostgreSQL、Workflow/Execution ORM、OperatorActionGovernanceService、WorkflowExecutionService。
"""

from __future__ import annotations

import os
from types import SimpleNamespace
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
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService
from app.services.workflow.execution import WorkflowExecutionService


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_database_integration() -> None:
    """真实 PostgreSQL 测试必须由显式 Gate 开启，避免普通回归隐式依赖数据库。"""
    if os.getenv("RUN_DATABASE_INTEGRATION") != "1":
        pytest.skip("需要设置 RUN_DATABASE_INTEGRATION=1 才执行 Execution Governance PostgreSQL 验收")


@pytest_asyncio.fixture(autouse=True)
async def reset_database_engine_pool() -> None:
    """隔离 pytest-asyncio 事件循环，避免 asyncpg 连接跨测试循环复用。"""
    await engine.dispose()
    try:
        yield
    finally:
        await engine.dispose()


async def _create_fixture(tenant_id, user_id, *, execution_status: str = "pending"):
    """创建最小 Tenant/User/Published Workflow/Execution 前置事实。"""
    workflow_id = uuid4()
    version_id = uuid4()
    execution_id = uuid4()
    async with SessionLocal() as session:
        async with session.begin():
            session.add(Tenant(id=tenant_id, name=f"execution-governance-{tenant_id}"))
            session.add(User(
                id=user_id,
                username=f"execution-governance-{user_id}",
                password_hash="integration-test",
                tenant_id=tenant_id,
            ))
            workflow = Workflow(
                id=workflow_id,
                name=f"execution-governance-{workflow_id}",
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
            session.add(WorkflowExecution(
                id=execution_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                workflow_version_id=version_id,
                created_by=user_id,
                status=execution_status,
                input_data={"source": "operator-execution-acceptance"},
            ))
    return workflow_id, version_id, execution_id


async def _cleanup(*tenant_ids, user_ids) -> None:
    """清理本测试生成的审计、幂等、Trace、Execution、Workflow 与身份。"""
    async with SessionLocal() as session:
        await session.execute(delete(AuditLog).where(AuditLog.tenant_id.in_(tenant_ids)))
        await session.execute(delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id.in_(tenant_ids)))
        await session.execute(delete(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id.in_(tenant_ids)))
        await session.execute(delete(WorkflowExecution).where(WorkflowExecution.tenant_id.in_(tenant_ids)))
        await session.execute(delete(WorkflowVersion).where(WorkflowVersion.created_by.in_(user_ids)))
        await session.execute(delete(Workflow).where(Workflow.owner_id.in_(user_ids)))
        await session.execute(delete(User).where(User.id.in_(user_ids)))
        await session.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))
        await session.commit()


@pytest.mark.asyncio
async def test_operator_execution_run_persists_state_and_operator_audit(monkeypatch) -> None:
    """验证 Run 的 Execution 状态与 Operator Audit 在同一治理事务中成功提交。"""
    tenant_id = uuid4()
    user_id = uuid4()
    workflow_id, version_id, execution_id = await _create_fixture(tenant_id, user_id, execution_status="pending")

    async def fake_run(self, execution, version, actor_id, is_admin, *, commit=True):
        """模拟已通过领域校验的 Run 最小状态变更，不复制生产状态机。"""
        assert commit is False
        execution.status = "running"
        return execution

    monkeypatch.setattr(WorkflowExecutionService, "run", fake_run)
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            result = await service.execute_execution(
                execution_id, tenant_id, user_id, True, "run",
            )
            assert result.id == execution_id
            assert result.status == "running"

        async with SessionLocal() as session:
            execution = (await session.execute(select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == tenant_id,
            ))).scalar_one()
            audit = (await session.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.resource_id == str(execution_id),
                AuditLog.action == "operator.workflow_execution.run",
            ))).scalar_one()
            assert execution.status == "running"
            assert audit.workflow_id == workflow_id
            assert audit.workflow_version_id == version_id
            assert audit.workflow_execution_id == execution_id
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])


@pytest.mark.asyncio
async def test_operator_execution_cancel_persists_state_and_operator_audit(monkeypatch) -> None:
    """验证 Cancel 的 Execution 状态与 Operator Audit 在同一治理事务中成功提交。"""
    tenant_id = uuid4()
    user_id = uuid4()
    _, _, execution_id = await _create_fixture(tenant_id, user_id, execution_status="running")

    async def fake_cancel(self, execution, actor_id, reason, *, commit=True):
        """模拟已通过领域校验的 Cancel 最小状态变更，不复制生产状态机。"""
        assert commit is False
        assert reason == "operator acceptance"
        execution.status = "cancelled"
        return execution

    monkeypatch.setattr(WorkflowExecutionService, "cancel", fake_cancel)
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            result = await service.execute_execution(
                execution_id, tenant_id, user_id, True, "cancel", confirm=True, reason="operator acceptance",
            )
            assert result.status == "cancelled"

        async with SessionLocal() as session:
            execution = (await session.execute(select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == tenant_id,
            ))).scalar_one()
            audit = (await session.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.resource_id == str(execution_id),
                AuditLog.action == "operator.workflow_execution.cancel",
            ))).scalar_one()
            assert execution.status == "cancelled"
            assert audit.workflow_execution_id == execution_id
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])


@pytest.mark.asyncio
async def test_operator_execution_rejects_invalid_state_without_audit() -> None:
    """验证 Run 不允许从非 pending 状态执行，且非法请求不产生 Operator Audit。"""
    tenant_id = uuid4()
    user_id = uuid4()
    _, _, execution_id = await _create_fixture(tenant_id, user_id, execution_status="running")
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            with pytest.raises(HTTPException) as exc_info:
                await service.execute_execution(
                    execution_id, tenant_id, user_id, True, "run",
                )
            assert exc_info.value.status_code == 409

        async with SessionLocal() as session:
            audits = (await session.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.resource_id == str(execution_id),
                AuditLog.action == "operator.workflow_execution.run",
            ))).scalars().all()
            execution = (await session.execute(select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == tenant_id,
            ))).scalar_one()
            assert audits == []
            assert execution.status == "running"
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])


@pytest.mark.asyncio
async def test_operator_execution_rolls_back_state_and_audit_when_finalization_fails(monkeypatch) -> None:
    """验证 Run 状态变更后最终审计失败时，Execution 与治理事实全部回滚。"""
    tenant_id = uuid4()
    user_id = uuid4()
    _, _, execution_id = await _create_fixture(tenant_id, user_id, execution_status="pending")

    async def fake_run(self, execution, version, actor_id, is_admin, *, commit=True):
        """模拟领域层状态变更，验证治理层最终化失败的数据库回滚。"""
        assert commit is False
        execution.status = "running"
        return execution

    monkeypatch.setattr(WorkflowExecutionService, "run", fake_run)
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            service._audit = AsyncMock(side_effect=RuntimeError("operator audit failure"))
            with pytest.raises(RuntimeError, match="operator audit failure"):
                await service.execute_execution(
                    execution_id, tenant_id, user_id, True, "run",
                )

        async with SessionLocal() as session:
            execution = (await session.execute(select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == tenant_id,
            ))).scalar_one()
            audits = (await session.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.resource_id == str(execution_id),
                AuditLog.action == "operator.workflow_execution.run",
            ))).scalars().all()
            idempotency = (await session.execute(select(OperatorActionIdempotency).where(
                OperatorActionIdempotency.tenant_id == tenant_id,
            ))).scalars().all()
            assert execution.status == "pending"
            assert audits == []
            assert idempotency == []
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])
