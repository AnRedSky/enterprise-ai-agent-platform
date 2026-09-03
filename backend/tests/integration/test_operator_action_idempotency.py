"""Operator Action PostgreSQL 集成测试：验证幂等键并发 claim、冲突语义与租户隔离。

职责：验证 OperatorActionIdempotency 的数据库唯一约束、原子 claim 与既有幂等结果语义。
边界：不执行实际 Workflow / Trigger 业务动作，不启动任何服务，不覆盖 HTTP API。
关键依赖：真实 PostgreSQL、OperatorActionIdempotency 模型与 OperatorActionGovernanceService。
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.infrastructure.db import SessionLocal
from app.infrastructure.db.session import engine
from app.models.core import Tenant, User
from app.models.operator_action import OperatorActionIdempotency
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
    """清理本测试生成的持久化身份与幂等事实。"""
    async with SessionLocal() as cleanup_session:
        await cleanup_session.execute(
            delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id.in_(tenant_ids))
        )
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

        # INSERT ... ON CONFLICT DO NOTHING 只能让一个事务真正创建幂等事实；另一个事务必须读取已提交事实。
        assert (first is None) != (second is None)
        existing = first or second
        assert existing is not None
        assert existing.tenant_id == tenant_id
        assert existing.idempotency_key == key
        assert existing.resource_id == resource_id
        assert existing.action == "retry"
        assert existing.status == "started"

        # tenant_id 是唯一约束的一部分，相同 Idempotency-Key 不得跨租户冲突。
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
            record = OperatorActionIdempotency(
                tenant_id=tenant_id,
                actor_id=user_id,
                resource_type="workflow_execution",
                resource_id=resource_id,
                action="retry",
                idempotency_key=key,
                status="failed",
                error_code="OPERATOR_ACTION_FAILED",
            )
            session.add(record)
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
