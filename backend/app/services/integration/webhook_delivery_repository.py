"""Webhook Delivery Fact 的租约与状态持久化边界。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.webhook_delivery import WebhookDelivery


class WebhookDeliveryRepository:
    """提供 tenant-scoped、skip-locked 的 Webhook Delivery Claim。"""

    async def claim_next(
        self,
        db: AsyncSession,
        now: datetime,
        owner: str,
        lease_seconds: int = 60,
        max_attempts: int = 5,
    ) -> WebhookDelivery | None:
        """原子领取一个待投递或租约已过期的 Delivery Fact。"""
        if not owner.strip():
            raise ValueError("owner 不能为空")
        if lease_seconds <= 0 or max_attempts <= 0:
            raise ValueError("lease_seconds 和 max_attempts 必须大于 0")
        claimable = or_(
            WebhookDelivery.status == "pending",
            (WebhookDelivery.status == "running") & (WebhookDelivery.lease_expires_at <= now),
        )
        result = await db.execute(
            select(WebhookDelivery)
            .options(
                selectinload(WebhookDelivery.destination),
                selectinload(WebhookDelivery.integration_event),
            )
            .where(
                claimable,
                WebhookDelivery.attempt_count < max_attempts,
                or_(WebhookDelivery.next_attempt_at.is_(None), WebhookDelivery.next_attempt_at <= now),
            )
            .order_by(WebhookDelivery.created_at, WebhookDelivery.id)
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

    async def mark_delivered(
        self, db: AsyncSession, delivery_id: uuid.UUID, owner: str, now: datetime, status_code: int
    ) -> bool:
        """仅允许当前 lease owner 完成投递。"""
        result = await db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.status == "running",
                WebhookDelivery.lease_owner == owner,
            ).with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        record.status = "delivered"
        record.delivered_at = now
        record.response_status_code = status_code
        record.lease_owner = None
        record.lease_expires_at = None
        record.next_attempt_at = None
        await db.flush()
        return True

    async def mark_failed(
        self,
        db: AsyncSession,
        delivery_id: uuid.UUID,
        owner: str,
        now: datetime,
        error_code: str,
        error_message: str,
        retry_at: datetime | None,
    ) -> bool:
        """记录失败；无 retry_at 时进入 dead_letter。"""
        result = await db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.status == "running",
                WebhookDelivery.lease_owner == owner,
            ).with_for_update()
        )
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
