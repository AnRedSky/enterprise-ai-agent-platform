"""Integration Event 领域 Repository。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.services.integration.contract import IntegrationEvent


class IntegrationEventRepository:
    """Durable Event 的 PostgreSQL 数据访问边界。"""

    async def create(self, db: AsyncSession, event: IntegrationEvent) -> IntegrationEventRecord:
        record = IntegrationEventRecord(
            id=event.event_id,
            tenant_id=event.tenant_id,
            event_type=event.event_type,
            schema_version=event.schema_version,
            source=event.source,
            subject=event.subject,
            idempotency_key=event.idempotency_key,
            occurred_at=event.occurred_at.replace(tzinfo=None),
            request_id=event.request_id,
            trace_id=event.trace_id,
            payload=event.payload,
            metadata_json=event.metadata,
            status="pending",
            attempt_count=0,
        )
        db.add(record)
        await db.flush()
        return record

    async def get(self, db: AsyncSession, tenant_id: uuid.UUID, event_id: uuid.UUID) -> IntegrationEventRecord | None:
        result = await db.execute(
            select(IntegrationEventRecord).where(
                IntegrationEventRecord.tenant_id == tenant_id,
                IntegrationEventRecord.id == event_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(
        self, db: AsyncSession, tenant_id: uuid.UUID, now: datetime, limit: int = 100
    ) -> list[IntegrationEventRecord]:
        if limit < 1:
            raise ValueError("limit 必须大于 0")
        result = await db.execute(
            select(IntegrationEventRecord)
            .where(
                IntegrationEventRecord.tenant_id == tenant_id,
                IntegrationEventRecord.status == "pending",
                (IntegrationEventRecord.next_attempt_at.is_(None) | (IntegrationEventRecord.next_attempt_at <= now)),
            )
            .order_by(IntegrationEventRecord.created_at, IntegrationEventRecord.id)
            .limit(limit)
        )
        return list(result.scalars().all())
