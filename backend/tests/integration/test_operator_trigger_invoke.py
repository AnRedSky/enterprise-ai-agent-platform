"""Operator Trigger Invoke PostgreSQL 集成测试：验证幂等重放与治理事务原子性。

职责：使用真实 PostgreSQL 验证 Manual Trigger Operator Action 的 Result Resource、幂等记录、Audit、Trace 与 Integration Event 一致性。
边界：不覆盖 HTTP API，不启动任何服务；Workflow Runtime 使用最小 input 节点定义。
关键依赖：真实 PostgreSQL、Workflow/Trigger/Execution ORM、OperatorActionGovernanceService。
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, update

from app.infrastructure.db import SessionLocal
from app.infrastructure.db.session import engine
from app.models.core import AuditLog, Tenant, User
from app.models.integration_event import IntegrationEventRecord
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.models.workflow_trigger import WorkflowTrigger
from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_database_integration() -> None:
    """真实 PostgreSQL 测试必须由显式 Gate 开启，避免普通回归隐式依赖数据库。"""
    if os.getenv("RUN_DATABASE_INTEGRATION") != "1":
        pytest.skip("需要设置 RUN_DATABASE_INTEGRATION=1 才执行 Trigger Invoke PostgreSQL 验收")


@pytest_asyncio.fixture(autouse=True)
async def reset_database_engine_pool() -> None:
    """隔离 pytest-asyncio 事件循环，避免 asyncpg 连接跨测试循环复用。"""
    await engine.dispose()
    try:
        yield
    finally:
        await engine.dispose()


async def _create_fixture(tenant_id, user_id):
    """创建已发布 Workflow、Version 与 enabled Manual Trigger，严格按外键依赖顺序写入。"""
    workflow_id = uuid4()
    version_id = uuid4()
    trigger_id = uuid4()
    async with SessionLocal() as session:
        async with session.begin():
            session.add(Tenant(id=tenant_id, name=f"trigger-invoke-{tenant_id}"))
            session.add(User(
                id=user_id,
                username=f"trigger-invoke-{user_id}",
                password_hash="integration-test",
                tenant_id=tenant_id,
            ))
            workflow = Workflow(
                id=workflow_id,
                name=f"trigger-invoke-{workflow_id}",
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
            await session.execute(
                update(Workflow)
                .where(Workflow.id == workflow_id)
                .values(published_version_id=version_id)
            )
            trigger = WorkflowTrigger(
                id=trigger_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                name=f"manual-{trigger_id}",
                trigger_type="manual",
                status="enabled",
                created_by=user_id,
                config={},
            )
            session.add(trigger)
            await session.flush()
    return workflow_id, version_id, trigger_id


async def _cleanup(tenant_id, user_id) -> None:
    """清理本测试生成的 Trigger、Execution、Integration Event、审计、幂等事实与身份。"""
    async with SessionLocal() as session:
        await session.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
        await session.execute(delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id == tenant_id))
        await session.execute(delete(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id == tenant_id))
        await session.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id == tenant_id))
        await session.execute(delete(WorkflowExecution).where(WorkflowExecution.tenant_id == tenant_id))
        await session.execute(delete(WorkflowTrigger).where(WorkflowTrigger.tenant_id == tenant_id))
        await session.execute(delete(WorkflowVersion).where(WorkflowVersion.created_by == user_id))
        await session.execute(delete(Workflow).where(Workflow.owner_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
        await session.commit()


@pytest.mark.asyncio
async def test_operator_trigger_invoke_replay_reuses_execution_and_does_not_duplicate_audit() -> None:
    """验证 Trigger Invoke 成功后同 key 重放复用同一 Execution 且不重复生成 Operator Audit。"""
    tenant_id = uuid4()
    user_id = uuid4()
    key = f"trigger-invoke-replay-{uuid4()}"
    workflow_id, _, trigger_id = await _create_fixture(tenant_id, user_id)
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            first = await service.execute_trigger(
                trigger_id, tenant_id, user_id, True, "invoke", confirm=True,
                input_data={"source": "operator-acceptance"}, idempotency_key=key,
            )
            first_id = first.id

        async with SessionLocal() as session:
            record = (await session.execute(select(OperatorActionIdempotency).where(
                OperatorActionIdempotency.tenant_id == tenant_id,
                OperatorActionIdempotency.idempotency_key == key,
            ))).scalar_one()
            operator_audit_count = (await session.execute(select(func.count()).select_from(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.operator_action_id == record.id,
            ))).scalar_one()
            execution_count = (await session.execute(select(func.count()).select_from(WorkflowExecution).where(
                WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.id == first_id,
            ))).scalar_one()
            assert record.status == "succeeded"
            assert record.result_resource_type == "workflow_execution"
            assert record.result_resource_id == first_id
            assert execution_count == 1
            assert operator_audit_count == 1

        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            replay = await service.execute_trigger(
                trigger_id, tenant_id, user_id, True, "invoke", confirm=True,
                input_data={"source": "operator-replay"}, idempotency_key=key,
            )
            assert replay.id == first_id

        async with SessionLocal() as session:
            record = (await session.execute(select(OperatorActionIdempotency).where(
                OperatorActionIdempotency.tenant_id == tenant_id,
                OperatorActionIdempotency.idempotency_key == key,
            ))).scalar_one()
            operator_audit_count = (await session.execute(select(func.count()).select_from(AuditLog).where(
                AuditLog.tenant_id == tenant_id, AuditLog.operator_action_id == record.id,
            ))).scalar_one()
            execution_count = (await session.execute(select(func.count()).select_from(WorkflowExecution).where(
                WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.id == first_id,
            ))).scalar_one()
            assert operator_audit_count == 1
            assert execution_count == 1
            assert record.result_resource_id == first_id
            assert workflow_id is not None
    finally:
        await _cleanup(tenant_id, user_id)


@pytest.mark.asyncio
async def test_operator_trigger_invoke_rolls_back_execution_idempotency_audit_trace_and_event_on_finalization_failure() -> None:
    """验证 Invoke 最终 Audit 失败时 Execution、幂等、Audit、Trace 与 Integration Event 全部回滚。"""
    tenant_id = uuid4()
    user_id = uuid4()
    key = f"trigger-invoke-rollback-{uuid4()}"
    workflow_id, _, trigger_id = await _create_fixture(tenant_id, user_id)
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            service._audit = AsyncMock(side_effect=RuntimeError("operator audit failure"))
            with pytest.raises(RuntimeError, match="operator audit failure"):
                await service.execute_trigger(
                    trigger_id, tenant_id, user_id, True, "invoke", confirm=True,
                    input_data={"source": "operator-rollback"}, idempotency_key=key,
                )

        async with SessionLocal() as session:
            assert (await session.execute(select(OperatorActionIdempotency).where(
                OperatorActionIdempotency.tenant_id == tenant_id,
                OperatorActionIdempotency.idempotency_key == key,
            ))).scalar_one_or_none() is None
            assert (await session.execute(select(WorkflowExecution).where(
                WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.idempotency_key == key,
            ))).scalar_one_or_none() is None
            assert (await session.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.resource_id == str(trigger_id),
                AuditLog.action.like("operator.workflow_trigger.invoke%"),
            ))).scalars().all() == []
            assert (await session.execute(select(WorkflowTraceEvent).where(
                WorkflowTraceEvent.tenant_id == tenant_id,
                WorkflowTraceEvent.event_type == "trigger.invoked",
            ))).scalars().all() == []
            assert (await session.execute(select(IntegrationEventRecord).where(
                IntegrationEventRecord.tenant_id == tenant_id,
            ))).scalars().all() == []
            assert workflow_id is not None
    finally:
        await _cleanup(tenant_id, user_id)
