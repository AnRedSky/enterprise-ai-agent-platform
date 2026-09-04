"""Operator Action PostgreSQL 集成测试：验证幂等键并发、结果复用、事务原子性与租户隔离。

职责：验证 OperatorActionIdempotency 的数据库唯一约束、原子 claim、成功结果复用以及治理事务事实一致性。
边界：不覆盖 HTTP API，不启动任何服务；业务执行仅使用真实 Workflow Execution 持久化链路。
关键依赖：真实 PostgreSQL、Workflow/Execution ORM、OperatorActionGovernanceService。
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import delete, func, select

from app.infrastructure.db import SessionLocal
from app.infrastructure.db.session import engine
from app.models.core import AuditLog, Tenant, User
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_database_integration() -> None:
    """真实 PostgreSQL 测试必须由显式 Gate 开启，避免普通回归隐式依赖数据库。"""
    if os.getenv("RUN_DATABASE_INTEGRATION") != "1":
        pytest.skip("需要设置 RUN_DATABASE_INTEGRATION=1 才执行 Operator Action PostgreSQL 验收")


@pytest_asyncio.fixture(autouse=True)
async def reset_database_engine_pool() -> None:
    """隔离 pytest-asyncio 事件循环，避免 asyncpg 连接跨测试循环复用。"""
    await engine.dispose()
    try:
        yield
    finally:
        await engine.dispose()


async def _create_identity(tenant_id, user_id) -> None:
    """创建本测试需要的最小 Tenant/User 前置事实。"""
    async with SessionLocal() as session:
        async with session.begin():
            session.add(Tenant(id=tenant_id, name=f"operator-idempotency-{tenant_id}"))
            session.add(
                User(
                    id=user_id,
                    username=f"operator-idempotency-{user_id}",
                    password_hash="integration-test",
                    tenant_id=tenant_id,
                )
            )


async def _create_failed_execution(tenant_id, user_id):
    """创建可用于 Retry 治理验收的最小已发布 Workflow 与 failed Execution。"""
    workflow_id = uuid4()
    version_id = uuid4()
    execution_id = uuid4()
    async with SessionLocal() as session:
        async with session.begin():
            # WorkflowVersion.workflow_id 与 Workflow.published_version_id 构成互相依赖，必须分阶段 flush。
            workflow = Workflow(
                id=workflow_id,
                name=f"operator-governance-{workflow_id}",
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
            execution = WorkflowExecution(
                id=execution_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                workflow_version_id=version_id,
                created_by=user_id,
                status="failed",
                input_data={"source": "operator-acceptance"},
                error_code="TEST_FAILED",
            )
            session.add(execution)
    return workflow_id, version_id, execution_id


async def _claim_and_commit(tenant_id, user_id, resource_id, key):
    """在独立数据库事务中竞争同一个幂等键，并提交 claim 结果。"""
    async with SessionLocal() as session:
        service = OperatorActionGovernanceService(session)
        record = await service._claim_idempotency(
            tenant_id=tenant_id,
            actor_id=user_id,
            resource_type="workflow_execution",
            resource_id=resource_id,
            action="retry",
            idempotency_key=key,
        )
        await session.commit()
        return record


async def _cleanup(*tenant_ids, user_ids) -> None:
    """清理本测试生成的 Workflow、Execution、审计、幂等事实与身份。"""
    async with SessionLocal() as cleanup_session:
        await cleanup_session.execute(delete(AuditLog).where(AuditLog.tenant_id.in_(tenant_ids)))
        await cleanup_session.execute(
            delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id.in_(tenant_ids))
        )
        await cleanup_session.execute(delete(WorkflowExecution).where(WorkflowExecution.tenant_id.in_(tenant_ids)))
        await cleanup_session.execute(delete(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id.in_(tenant_ids)))
        await cleanup_session.execute(delete(WorkflowVersion).where(WorkflowVersion.created_by.in_(user_ids)))
        await cleanup_session.execute(delete(Workflow).where(Workflow.owner_id.in_(user_ids)))
        await cleanup_session.execute(delete(User).where(User.id.in_(user_ids)))
        await cleanup_session.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))
        await cleanup_session.commit()


@pytest.mark.asyncio
async def test_operator_action_idempotency_concurrent_claim_has_single_winner_and_tenant_isolation() -> None:
    """验证同租户并发 claim 只有一个新建者，同时相同 key 在不同 tenant 可以独立使用。"""
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    user_id = uuid4()
    other_user_id = uuid4()
    resource_id = uuid4()
    other_resource_id = uuid4()
    key = f"operator-race-{uuid4()}"

    await _create_identity(tenant_id, user_id)
    await _create_identity(other_tenant_id, other_user_id)
    try:
        first, second = await asyncio.gather(
            _claim_and_commit(tenant_id, user_id, resource_id, key),
            _claim_and_commit(tenant_id, user_id, resource_id, key),
        )
        assert (first is None) != (second is None)
        existing = first or second
        assert existing is not None
        assert existing.tenant_id == tenant_id
        assert existing.idempotency_key == key
        assert existing.resource_id == resource_id
        assert existing.action == "retry"
        assert existing.status == "started"

        async with SessionLocal() as other_session:
            other_service = OperatorActionGovernanceService(other_session)
            other_record = await other_service._claim_idempotency(
                tenant_id=other_tenant_id,
                actor_id=other_user_id,
                resource_type="workflow_execution",
                resource_id=other_resource_id,
                action="retry",
                idempotency_key=key,
            )
            assert other_record is None
            await other_session.commit()
    finally:
        await _cleanup(tenant_id, other_tenant_id, user_ids=[user_id, other_user_id])


@pytest.mark.asyncio
async def test_operator_action_idempotency_rejects_same_key_for_different_resource() -> None:
    """验证同租户 Idempotency-Key 不能跨资源或操作复用。"""
    tenant_id = uuid4()
    user_id = uuid4()
    first_resource_id = uuid4()
    second_resource_id = uuid4()
    key = f"operator-conflict-{uuid4()}"

    await _create_identity(tenant_id, user_id)
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            assert await service._claim_idempotency(
                tenant_id=tenant_id, actor_id=user_id, resource_type="workflow_execution",
                resource_id=first_resource_id, action="retry", idempotency_key=key,
            ) is None
            await session.commit()

        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            with pytest.raises(HTTPException) as exc_info:
                await service._claim_idempotency(
                    tenant_id=tenant_id, actor_id=user_id, resource_type="workflow_execution",
                    resource_id=second_resource_id, action="retry", idempotency_key=key,
                )
            assert exc_info.value.status_code == 409
            await session.rollback()
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])


@pytest.mark.asyncio
async def test_operator_action_idempotency_failed_record_cannot_be_reused_as_success() -> None:
    """验证已失败的幂等请求不能伪装成成功结果复用，避免同 key 静默重复执行。"""
    tenant_id = uuid4()
    user_id = uuid4()
    resource_id = uuid4()
    key = f"operator-failed-{uuid4()}"

    await _create_identity(tenant_id, user_id)
    try:
        async with SessionLocal() as session:
            session.add(OperatorActionIdempotency(
                tenant_id=tenant_id, actor_id=user_id, resource_type="workflow_execution",
                resource_id=resource_id, action="retry", idempotency_key=key,
                status="failed", error_code="OPERATOR_ACTION_FAILED",
            ))
            await session.commit()

        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            existing = (await session.execute(select(OperatorActionIdempotency).where(
                OperatorActionIdempotency.tenant_id == tenant_id,
                OperatorActionIdempotency.idempotency_key == key,
            ))).scalar_one()
            with pytest.raises(HTTPException) as exc_info:
                await service._reuse_or_raise(existing)
            assert exc_info.value.status_code == 409
            await session.rollback()
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])


@pytest.mark.asyncio
async def test_operator_action_retry_replay_reuses_result_and_does_not_duplicate_audit() -> None:
    """验证 Retry 成功后同 key 重放复用同一 Result Resource，且不会再次写入 Operator Audit。"""
    tenant_id = uuid4()
    user_id = uuid4()
    key = f"operator-replay-{uuid4()}"
    await _create_identity(tenant_id, user_id)
    _, _, execution_id = await _create_failed_execution(tenant_id, user_id)

    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            first = await service.execute_execution(
                execution_id, tenant_id, user_id, True, "retry", confirm=True, idempotency_key=key,
            )
            first_result_id = first.id

        async with SessionLocal() as session:
            idempotency = (await session.execute(select(OperatorActionIdempotency).where(
                OperatorActionIdempotency.tenant_id == tenant_id,
                OperatorActionIdempotency.idempotency_key == key,
            ))).scalar_one()
            audit_count = (await session.execute(select(func.count()).select_from(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.operator_action_id == idempotency.id,
            ))).scalar_one()
            assert idempotency.status == "succeeded"
            assert idempotency.result_resource_type == "workflow_execution"
            assert idempotency.result_resource_id == first_result_id
            assert audit_count == 1

        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            replay = await service.execute_execution(
                execution_id, tenant_id, user_id, True, "retry", confirm=True, idempotency_key=key,
            )
            assert replay.id == first_result_id
            await session.commit()

        async with SessionLocal() as session:
            idempotency = (await session.execute(select(OperatorActionIdempotency).where(
                OperatorActionIdempotency.tenant_id == tenant_id,
                OperatorActionIdempotency.idempotency_key == key,
            ))).scalar_one()
            execution_count = (await session.execute(select(func.count()).select_from(WorkflowExecution).where(
                WorkflowExecution.tenant_id == tenant_id,
                WorkflowExecution.retry_of_execution_id == execution_id,
            ))).scalar_one()
            audit_count = (await session.execute(select(func.count()).select_from(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.operator_action_id == idempotency.id,
            ))).scalar_one()
            assert idempotency.result_resource_id == first_result_id
            assert execution_count == 1
            assert audit_count == 1
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])


@pytest.mark.asyncio
async def test_operator_action_retry_rolls_back_result_idempotency_audit_and_trace_on_finalization_failure(monkeypatch) -> None:
    """验证治理最终化失败时 Retry Result Resource、幂等事实、Audit 与 Trace 全部回滚。"""
    tenant_id = uuid4()
    user_id = uuid4()
    key = f"operator-rollback-{uuid4()}"
    await _create_identity(tenant_id, user_id)
    _, _, execution_id = await _create_failed_execution(tenant_id, user_id)

    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session)
            service._audit = AsyncMock(side_effect=RuntimeError("operator audit failure"))
            with pytest.raises(RuntimeError, match="operator audit failure"):
                await service.execute_execution(
                    execution_id, tenant_id, user_id, True, "retry", confirm=True, idempotency_key=key,
                )
            await session.rollback()

        async with SessionLocal() as session:
            assert (await session.execute(select(OperatorActionIdempotency).where(
                OperatorActionIdempotency.tenant_id == tenant_id,
                OperatorActionIdempotency.idempotency_key == key,
            ))).scalar_one_or_none() is None
            assert (await session.execute(select(WorkflowExecution).where(
                WorkflowExecution.tenant_id == tenant_id,
                WorkflowExecution.retry_of_execution_id == execution_id,
            ))).scalar_one_or_none() is None
            assert (await session.execute(select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.resource_id == str(execution_id),
                AuditLog.action.like("operator.workflow_execution.retry%"),
            ))).scalars().all() == []
            assert (await session.execute(select(WorkflowTraceEvent).where(
                WorkflowTraceEvent.tenant_id == tenant_id,
                WorkflowTraceEvent.execution_id == execution_id,
                WorkflowTraceEvent.event_type == "execution.retry_requested",
            ))).scalars().all() == []
    finally:
        await _cleanup(tenant_id, user_ids=[user_id])
