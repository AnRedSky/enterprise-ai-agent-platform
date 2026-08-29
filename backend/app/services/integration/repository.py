"""Integration Event 可靠投递的数据访问边界。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.services.integration.contract import IntegrationEvent


class IntegrationEventRepository:
    """负责 Durable Event 的租户隔离、幂等写入和原子投递租约。"""

    async def create(self, db: AsyncSession, event: IntegrationEvent) -> IntegrationEventRecord:
        """创建待投递事件，并由数据库唯一约束保证幂等。

        Args:
            db: 当前事务数据库会话。
            event: 已通过 Contract 校验的事件。
        Returns:
            新创建的 Durable Event 记录。
        """
        record = IntegrationEventRecord(
            id=event.event_id, tenant_id=event.tenant_id, event_type=event.event_type,
            schema_version=event.schema_version, source=event.source, subject=event.subject,
            idempotency_key=event.idempotency_key, occurred_at=event.occurred_at.replace(tzinfo=None),
            request_id=event.request_id, trace_id=event.trace_id, payload=event.payload,
            metadata_json=event.metadata, status="pending", attempt_count=0,
        )
        db.add(record)
        await db.flush()
        return record

    async def get(self, db: AsyncSession, tenant_id: uuid.UUID, event_id: uuid.UUID) -> IntegrationEventRecord | None:
        """按租户读取事件，禁止跨租户查询。"""
        result = await db.execute(select(IntegrationEventRecord).where(
            IntegrationEventRecord.tenant_id == tenant_id,
            IntegrationEventRecord.id == event_id,
        ))
        return result.scalar_one_or_none()

    async def claim_next(
        self, db: AsyncSession, tenant_id: uuid.UUID, owner: str, now: datetime,
        lease_seconds: int = 60, max_attempts: int = 5,
    ) -> IntegrationEventRecord | None:
        """原子领取一个可投递事件，处理过期租约并使用行锁避免多 Worker 重复领取。

        Args:
            db: 当前事务数据库会话；调用方负责提交事务。
            tenant_id: Worker 所属租户。
            owner: Worker 实例唯一标识。
            now: 当前 UTC 时间（无时区形式）。
            lease_seconds: 投递租约有效秒数。
            max_attempts: 超过次数后不再进入 retry。
        Returns:
            成功领取的事件；没有可领取事件时返回 ``None``。
        Raises:
            ValueError: 租约或最大尝试次数非法。
        """
        if lease_seconds <= 0 or max_attempts <= 0:
            raise ValueError("lease_seconds 和 max_attempts 必须大于 0")
        eligible = or_(
            IntegrationEventRecord.status == "pending",
            ((IntegrationEventRecord.status == "running") & (IntegrationEventRecord.lease_expires_at <= now)),
        )
        result = await db.execute(
            select(IntegrationEventRecord)
            .where(
                IntegrationEventRecord.tenant_id == tenant_id,
                eligible,
                IntegrationEventRecord.attempt_count < max_attempts,
                or_(IntegrationEventRecord.next_attempt_at.is_(None), IntegrationEventRecord.next_attempt_at <= now),
            )
            .order_by(IntegrationEventRecord.created_at, IntegrationEventRecord.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        record.status = "running"
        record.attempt_count += 1
        record.last_attempt_at = now
        record.lease_owner = owner
        record.lease_expires_at = now + timedelta(seconds=lease_seconds)
        record.last_error_code = None
        record.last_error_message = None
        await db.flush()
        return record

    async def mark_delivered(self, db: AsyncSession, record_id: uuid.UUID, owner: str, now: datetime) -> bool:
        """在当前租约仍归属 Worker 时将事件标记为已投递。"""
        result = await db.execute(select(IntegrationEventRecord).where(
            IntegrationEventRecord.id == record_id,
            IntegrationEventRecord.status == "running",
            IntegrationEventRecord.lease_owner == owner,
        ).with_for_update())
        record = result.scalar_one_or_none()
        if record is None:
            return False
        record.status = "delivered"
        record.delivered_at = now
        record.lease_owner = None
        record.lease_expires_at = None
        record.next_attempt_at = None
        await db.flush()
        return True

    async def mark_failed(
        self, db: AsyncSession, record_id: uuid.UUID, owner: str, now: datetime,
        error_code: str, error_message: str, retry_at: datetime | None,
    ) -> bool:
        """记录失败并根据调用方计算的退避时间决定 retry 或 dead-letter。"""
        result = await db.execute(select(IntegrationEventRecord).where(
            IntegrationEventRecord.id == record_id,
            IntegrationEventRecord.status == "running",
            IntegrationEventRecord.lease_owner == owner,
        ).with_for_update())
        record = result.scalar_one_or_none()
        if record is None:
            return False
        record.last_error_code = error_code[:100]
        record.last_error_message = error_message
        record.lease_owner = None
        record.lease_expires_at = None
        if retry_at is None:
            record.status = "dead_letter"
            record.next_attempt_at = None
        else:
            record.status = "pending"
            record.next_attempt_at = retry_at
        await db.flush()
        return True

    async def list_pending(self, db: AsyncSession, tenant_id: uuid.UUID, now: datetime, limit: int = 100) -> list[IntegrationEventRecord]:
        """按稳定顺序读取当前租户可重试事件。"""
        if limit < 1:
            raise ValueError("limit 必须大于 0")
        result = await db.execute(select(IntegrationEventRecord).where(
            IntegrationEventRecord.tenant_id == tenant_id,
            IntegrationEventRecord.status == "pending",
            or_(IntegrationEventRecord.next_attempt_at.is_(None), IntegrationEventRecord.next_attempt_at <= now),
        ).order_by(IntegrationEventRecord.created_at, IntegrationEventRecord.id).limit(limit))
        return list(result.scalars().all())
