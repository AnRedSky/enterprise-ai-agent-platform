"""Webhook Delivery Fact 的租约、状态、审计与 replay 持久化边界。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_delivery_audit import WebhookDeliveryAudit


class WebhookDeliveryRepository:
    """提供 tenant-scoped、skip-locked 的 Webhook Delivery Claim 与审计。"""

    async def claim_next(
        self,
        db: AsyncSession,
        now: datetime,
        owner: str,
        lease_seconds: int = 60,
        max_attempts: int = 5,
        tenant_id: uuid.UUID | None = None,
    ) -> WebhookDelivery | None:
        if not owner.strip():
            raise ValueError("owner 不能为空")
        if lease_seconds <= 0 or max_attempts <= 0:
            raise ValueError("lease_seconds 和 max_attempts 必须大于 0")
        claimable = or_(
            WebhookDelivery.status == "pending",
            (WebhookDelivery.status == "running") & (WebhookDelivery.lease_expires_at <= now),
        )
        stmt = (
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
        )
        if tenant_id is not None:
            stmt = stmt.where(WebhookDelivery.tenant_id == tenant_id)
        result = await db.execute(
            stmt.order_by(WebhookDelivery.created_at, WebhookDelivery.id)
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
        await self._audit(db, record, "claim", owner, "running")
        return record

    async def _audit(
        self,
        db: AsyncSession,
        record: WebhookDelivery,
        action: str,
        actor: str,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        db.add(
            WebhookDeliveryAudit(
                tenant_id=record.tenant_id,
                delivery_id=record.id,
                integration_event_id=record.integration_event_id,
                action=action,
                attempt_count=record.attempt_count,
                status=status,
                response_status_code=record.response_status_code,
                error_code=error_code,
                error_message=(error_message or "")[:2000] if error_message else None,
                actor=actor,
            )
        )
        await db.flush()

    async def mark_delivered(self, db: AsyncSession, delivery_id: uuid.UUID, owner: str, now: datetime, status_code: int) -> bool:
        result = await db.execute(
            select(WebhookDelivery)
            .where(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.status == "running",
                WebhookDelivery.lease_owner == owner,
            )
            .with_for_update()
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
        await self._audit(db, record, "delivered", owner, "delivered")
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
        response_status_code: int | None = None,
    ) -> bool:
        result = await db.execute(
            select(WebhookDelivery)
            .where(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.status == "running",
                WebhookDelivery.lease_owner == owner,
            )
            .with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        record.last_error_code = error_code[:100]
        record.last_error_message = error_message[:4000]
        record.response_status_code = response_status_code
        record.lease_owner = None
        record.lease_expires_at = None
        record.status = "dead_letter" if retry_at is None else "pending"
        record.next_attempt_at = retry_at
        await self._audit(db, record, "dead_letter" if retry_at is None else "retry", owner, record.status, error_code, error_message)
        return True

    async def replay(self, db: AsyncSession, tenant_id: uuid.UUID, delivery_id: uuid.UUID, actor: str) -> WebhookDelivery | None:
        result = await db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.id == delivery_id, WebhookDelivery.tenant_id == tenant_id)
            .with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        if record.status not in {"delivered", "dead_letter"}:
            raise ValueError("只有 delivered 或 dead_letter Delivery 才允许 replay")
        record.status = "pending"
        record.next_attempt_at = None
        record.lease_owner = None
        record.lease_expires_at = None
        record.delivered_at = None
        record.last_error_code = None
        record.last_error_message = None
        await self._audit(db, record, "replay", actor, "pending")
        return record

    async def get(self, db: AsyncSession, tenant_id: uuid.UUID, delivery_id: uuid.UUID) -> WebhookDelivery | None:
        return await db.scalar(
            select(WebhookDelivery).where(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.tenant_id == tenant_id,
            )
        )

    async def list(self, db: AsyncSession, tenant_id: uuid.UUID, status: str | None = None, limit: int = 100) -> list[WebhookDelivery]:
        if limit < 1 or limit > 500:
            raise ValueError("limit 必须在 1..500")
        stmt = select(WebhookDelivery).where(WebhookDelivery.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(WebhookDelivery.status == status)
        result = await db.execute(stmt.order_by(WebhookDelivery.created_at.desc(), WebhookDelivery.id.desc()).limit(limit))
        return list(result.scalars().all())

    async def list_audit(self, db: AsyncSession, tenant_id: uuid.UUID, delivery_id: uuid.UUID | None = None, limit: int = 100) -> list[WebhookDeliveryAudit]:
        if limit < 1 or limit > 500:
            raise ValueError("limit 必须在 1..500")
        stmt = select(WebhookDeliveryAudit).where(WebhookDeliveryAudit.tenant_id == tenant_id)
        if delivery_id is not None:
            stmt = stmt.where(WebhookDeliveryAudit.delivery_id == delivery_id)
        result = await db.execute(stmt.order_by(WebhookDeliveryAudit.created_at.desc(), WebhookDeliveryAudit.id.desc()).limit(limit))
        return list(result.scalars().all())
