"""Phase 2.9-C Reliable Event Delivery PostgreSQL 真实验收测试。

职责：验证 Durable Event 在真实 PostgreSQL 下的并发租约、租约恢复、fencing、重试与租户隔离。
边界：不启动 API、Worker、Scheduler、Redis 或其他服务；测试数据由测试自动创建并清理。
关键依赖：真实 PostgreSQL、已执行 Alembic head、应用数据库连接配置。
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from app.infrastructure.db.session import SessionLocal
from app.models.core import Tenant
from app.models.integration_event import IntegrationEventRecord
from app.services.integration.contract import IntegrationEvent
from app.services.integration.repository import IntegrationEventRepository

pytestmark = pytest.mark.real_api


def _event(tenant_id: uuid.UUID, *, key: str | None = None) -> IntegrationEvent:
    """创建本验收使用的唯一事件。

    Args:
        tenant_id: 事件所属租户。
        key: 可选幂等键。
    Returns:
        IntegrationEvent: 合法的 Durable Event Contract。
    """
    return IntegrationEvent(
        tenant_id=tenant_id,
        event_type="integration.delivery.acceptance",
        source="phase-2-9-c-real-gate",
        subject=f"acceptance-{uuid.uuid4()}",
        idempotency_key=key or str(uuid.uuid4()),
        payload={"fixture": True, "nonce": str(uuid.uuid4())},
    )


async def _create_tenant() -> uuid.UUID:
    """在真实 PostgreSQL 创建隔离租户并返回其标识。"""
    tenant_id = uuid.uuid4()
    async with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"phase-2-9-c-{tenant_id.hex}"))
        await db.commit()
    return tenant_id


async def _cleanup_tenant(tenant_id: uuid.UUID) -> None:
    """删除本验收创建的事件和租户，避免污染共享开发数据库。"""
    async with SessionLocal() as db:
        await db.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
        await db.commit()


async def _persist_event(tenant_id: uuid.UUID) -> uuid.UUID:
    """通过正式 Repository 将事件持久化到真实 PostgreSQL。"""
    event = _event(tenant_id)
    async with SessionLocal() as db:
        record = await IntegrationEventRepository().create(db, event)
        await db.commit()
        return record.id


@pytest.mark.asyncio
async def test_postgresql_concurrent_claim_allows_only_one_owner() -> None:
    """验证两个真实数据库事务并发 Claim 同一事件时只有一个租约持有者。"""
    tenant_id = await _create_tenant()
    try:
        event_id = await _persist_event(tenant_id)
        barrier = asyncio.Barrier(2)
        repository = IntegrationEventRepository()
        now = datetime.now(UTC).replace(tzinfo=None)

        async def claim(owner: str):
            await barrier.wait()
            async with SessionLocal() as db:
                item = await repository.claim_next(db, tenant_id, owner, now, 60, 5)
                await db.commit()
                return None if item is None else (item.id, item.lease_owner)

        results = await asyncio.gather(claim("real-worker-a"), claim("real-worker-b"))
        winners = [item for item in results if item is not None]
        assert len(winners) == 1
        assert winners[0][0] == event_id
        assert winners[0][1] in {"real-worker-a", "real-worker-b"}
    finally:
        await _cleanup_tenant(tenant_id)


@pytest.mark.asyncio
async def test_postgresql_expired_lease_can_be_reclaimed() -> None:
    """验证租约过期后另一 Worker 可以恢复领取同一事件。"""
    tenant_id = await _create_tenant()
    try:
        event_id = await _persist_event(tenant_id)
        repository = IntegrationEventRepository()
        first_now = datetime.now(UTC).replace(tzinfo=None)
        async with SessionLocal() as db:
            first = await repository.claim_next(db, tenant_id, "expired-worker", first_now, 1, 5)
            await db.commit()
            assert first is not None

        async with SessionLocal() as db:
            recovered = await repository.claim_next(
                db, tenant_id, "recovery-worker", first_now + timedelta(seconds=2), 60, 5
            )
            await db.commit()
            assert recovered is not None
            assert recovered.id == event_id
            assert recovered.lease_owner == "recovery-worker"
            assert recovered.attempt_count == 2
    finally:
        await _cleanup_tenant(tenant_id)


@pytest.mark.asyncio
async def test_postgresql_old_owner_is_fenced_after_reclaim() -> None:
    """验证旧租约 Worker 不能覆盖新租约 Worker 的最终状态。"""
    tenant_id = await _create_tenant()
    try:
        event_id = await _persist_event(tenant_id)
        repository = IntegrationEventRepository()
        first_now = datetime.now(UTC).replace(tzinfo=None)
        async with SessionLocal() as db:
            await repository.claim_next(db, tenant_id, "old-worker", first_now, 1, 5)
            await db.commit()
        recovery_now = first_now + timedelta(seconds=2)
        async with SessionLocal() as db:
            await repository.claim_next(db, tenant_id, "new-worker", recovery_now, 60, 5)
            await db.commit()
        async with SessionLocal() as db:
            stale_result = await repository.mark_delivered(db, event_id, "old-worker", recovery_now)
            await db.commit()
            assert stale_result is False
        async with SessionLocal() as db:
            fresh_result = await repository.mark_delivered(db, event_id, "new-worker", recovery_now)
            await db.commit()
            assert fresh_result is True
            persisted = (await db.execute(select(IntegrationEventRecord).where(IntegrationEventRecord.id == event_id))).scalar_one()
            assert persisted.status == "delivered"
            assert persisted.lease_owner is None
    finally:
        await _cleanup_tenant(tenant_id)


@pytest.mark.asyncio
async def test_postgresql_tenant_isolation_blocks_cross_tenant_claim() -> None:
    """验证事件只允许所属租户 Claim，其他租户即使知道事件 ID 也无法领取。"""
    owner_tenant = await _create_tenant()
    other_tenant = await _create_tenant()
    try:
        event_id = await _persist_event(owner_tenant)
        repository = IntegrationEventRepository()
        now = datetime.now(UTC).replace(tzinfo=None)
        async with SessionLocal() as db:
            wrong = await repository.claim_next(db, other_tenant, "wrong-tenant-worker", now, 60, 5)
            await db.commit()
            assert wrong is None
        async with SessionLocal() as db:
            right = await repository.claim_next(db, owner_tenant, "owner-worker", now, 60, 5)
            await db.commit()
            assert right is not None
            assert right.id == event_id
    finally:
        await _cleanup_tenant(owner_tenant)
        await _cleanup_tenant(other_tenant)


@pytest.mark.asyncio
async def test_postgresql_retry_and_dead_letter_state_machine() -> None:
    """验证失败事件可以 retry，达到最大尝试次数后进入 dead-letter。"""
    tenant_id = await _create_tenant()
    try:
        event_id = await _persist_event(tenant_id)
        repository = IntegrationEventRepository()
        now = datetime.now(UTC).replace(tzinfo=None)
        for attempt in range(1, 4):
            async with SessionLocal() as db:
                item = await repository.claim_next(db, tenant_id, f"retry-worker-{attempt}", now, 60, 3)
                await db.commit()
                assert item is not None
                retry_at = now + timedelta(seconds=attempt)
            async with SessionLocal() as db:
                failed = await repository.mark_failed(
                    db, event_id, f"retry-worker-{attempt}", now, "TEST_FAILURE", "deterministic failure", retry_at if attempt < 3 else None
                )
                await db.commit()
                assert failed is True
            if attempt < 3:
                now = retry_at + timedelta(seconds=1)

        async with SessionLocal() as db:
            persisted = (await db.execute(select(IntegrationEventRecord).where(IntegrationEventRecord.id == event_id))).scalar_one()
            assert persisted.status == "dead_letter"
            assert persisted.attempt_count == 3
            assert persisted.last_error_code == "TEST_FAILURE"
    finally:
        await _cleanup_tenant(tenant_id)
