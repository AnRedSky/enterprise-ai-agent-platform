"""Idempotent alert notification -> durable delivery routing.

This layer provides a stable notification identity and routing boundary. It does not
perform network I/O; WebhookDeliveryWorker remains the only delivery executor.
"""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_integration import WebhookDestination, WebhookSubscription
from app.services.integration.notification import NotificationRoutingService


class AlertNotificationDeliveryService:
    """Materialize alert notifications into tenant-scoped webhook delivery facts."""

    SUPPORTED_PROVIDERS = frozenset({"webhook_http"})

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def notification_key(event: IntegrationEventRecord, subscription: WebhookSubscription) -> str:
        """Stable identity for one alert transition and destination."""
        material = f"{event.tenant_id}:{event.event_type}:{event.id}:{subscription.destination_id}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    async def dispatch_event(self, event: IntegrationEventRecord) -> list[WebhookDelivery]:
        """Route exactly to matching destinations and atomically deduplicate delivery facts."""
        result = await self.db.execute(
            select(WebhookSubscription)
            .join(WebhookDestination, WebhookDestination.id == WebhookSubscription.destination_id)
            .where(
                WebhookSubscription.tenant_id == event.tenant_id,
                WebhookSubscription.event_type == event.event_type,
                WebhookSubscription.enabled.is_(True),
                WebhookDestination.tenant_id == event.tenant_id,
                WebhookDestination.enabled.is_(True),
                WebhookDestination.provider.in_(self.SUPPORTED_PROVIDERS),
            )
            .order_by(WebhookSubscription.priority, WebhookSubscription.id)
        )
        subscriptions = [
            subscription for subscription in result.scalars().all()
            if NotificationRoutingService._matches_filter(event.payload, subscription.filter_config)
        ]
        if not subscriptions:
            return []

        values = [
            {
                "id": uuid.uuid4(),
                "tenant_id": event.tenant_id,
                "subscription_id": subscription.id,
                "destination_id": subscription.destination_id,
                "integration_event_id": event.id,
                "status": "pending",
                "attempt_count": 0,
            }
            for subscription in subscriptions
        ]
        statement = (
            pg_insert(WebhookDelivery)
            .values(values)
            .on_conflict_do_nothing(constraint="uq_webhook_delivery_event_destination")
        )
        await self.db.execute(statement)
        await self.db.flush()

        deliveries = list((await self.db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.tenant_id == event.tenant_id,
                WebhookDelivery.integration_event_id == event.id,
                WebhookDelivery.destination_id.in_([s.destination_id for s in subscriptions]),
            ).order_by(WebhookDelivery.created_at, WebhookDelivery.id)
        )).scalars().all())
        return deliveries


__all__ = ["AlertNotificationDeliveryService"]
