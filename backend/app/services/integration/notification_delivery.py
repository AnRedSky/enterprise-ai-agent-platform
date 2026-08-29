"""Idempotent alert notification -> durable delivery routing.

This layer provides a stable notification identity and deduplication boundary. It does
not perform network I/O; WebhookDeliveryWorker remains the only delivery executor.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_integration import WebhookDestination, WebhookSubscription
from app.services.integration.notification import NotificationRoutingService


class AlertNotificationDeliveryService:
    """Materialize alert notifications into tenant-scoped webhook delivery facts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def notification_key(event: IntegrationEventRecord, subscription: WebhookSubscription) -> str:
        """Return a stable idempotency key for one alert transition and destination."""
        material = f"{event.tenant_id}:{event.event_type}:{event.subject}:{subscription.destination_id}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    async def dispatch_event(self, event: IntegrationEventRecord) -> list[WebhookDelivery]:
        """Create at most one delivery per alert event/destination, preserving tenant isolation."""
        subscriptions = list((await self.db.execute(
            select(WebhookSubscription)
            .join(WebhookDestination, WebhookDestination.id == WebhookSubscription.destination_id)
            .where(
                WebhookSubscription.tenant_id == event.tenant_id,
                WebhookSubscription.event_type == event.event_type,
                WebhookSubscription.enabled.is_(True),
                WebhookDestination.tenant_id == event.tenant_id,
                WebhookDestination.enabled.is_(True),
            )
            .order_by(WebhookSubscription.priority, WebhookSubscription.id)
        )).scalars().all())

        deliveries: list[WebhookDelivery] = []
        router = NotificationRoutingService(self.db)
        for subscription in subscriptions:
            if not router._matches_filter(event.payload, subscription.filter_config):
                continue
            existing = await self.db.scalar(select(WebhookDelivery).where(
                WebhookDelivery.tenant_id == event.tenant_id,
                WebhookDelivery.destination_id == subscription.destination_id,
                WebhookDelivery.integration_event_id == event.id,
            ))
            if existing is not None:
                deliveries.append(existing)
                continue
            deliveries.extend(await router.route_event(event))
            break
        return deliveries


__all__ = ["AlertNotificationDeliveryService"]
