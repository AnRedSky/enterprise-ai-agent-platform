"""Batch dispatcher for durable Integration Events.

The dispatcher is intentionally side-effect bounded: it only materializes Delivery
Facts. Delivery execution, retry and dead-letter transitions stay in the existing
WebhookDeliveryWorker.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.services.integration.notification import NotificationRoutingService


class NotificationDispatcher:
    """Route pending durable events without crossing tenant boundaries."""

    def __init__(self, db: AsyncSession, *, batch_size: int = 100):
        if batch_size < 1 or batch_size > 1000:
            raise ValueError("batch_size must be between 1 and 1000")
        self.db = db
        self.batch_size = batch_size
        self.router = NotificationRoutingService(db)

    async def dispatch_tenant(self, tenant_id: uuid.UUID) -> int:
        """Materialize deliveries for at most ``batch_size`` tenant events."""
        result = await self.db.execute(
            select(IntegrationEventRecord)
            .where(
                IntegrationEventRecord.tenant_id == tenant_id,
                IntegrationEventRecord.status == "pending",
            )
            .order_by(IntegrationEventRecord.occurred_at, IntegrationEventRecord.id)
            .limit(self.batch_size)
        )
        events = list(result.scalars().all())
        created = 0
        for event in events:
            created += len(await self.router.route_event(event))
        return created


__all__ = ["NotificationDispatcher"]
