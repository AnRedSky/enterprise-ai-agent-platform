"""Durable Integration Event -> Notification/Delivery routing.

This module intentionally stops at durable Delivery Fact creation. Network I/O remains
owned by the Webhook Delivery Worker, preserving the transaction boundary between
business facts and asynchronous delivery.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_integration import WebhookDestination, WebhookSubscription


class NotificationRoutingService:
    """Route one tenant-scoped integration event to enabled webhook subscriptions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def route_event(self, event: IntegrationEventRecord) -> list[WebhookDelivery]:
        """Create durable delivery facts for all matching subscriptions.

        Matching is deterministic and tenant-scoped. ``filter_config`` supports a
        small safe subset: ``{"key": expected_value}`` exact payload matching.
        Unknown/invalid filter shapes fail closed instead of broadening delivery.
        """
        subscriptions = list((await self.db.execute(
            select(WebhookSubscription)
            .join(
                WebhookDestination,
                WebhookDestination.id == WebhookSubscription.destination_id,
            )
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
        for subscription in subscriptions:
            if not self._matches_filter(event.payload, subscription.filter_config):
                continue
            delivery = WebhookDelivery(
                tenant_id=event.tenant_id,
                subscription_id=subscription.id,
                destination_id=subscription.destination_id,
                integration_event_id=event.id,
                status="pending",
                attempt_count=0,
            )
            try:
                async with self.db.begin_nested():
                    self.db.add(delivery)
                    await self.db.flush()
                deliveries.append(delivery)
            except IntegrityError:
                existing = await self.db.scalar(
                    select(WebhookDelivery).where(
                        WebhookDelivery.tenant_id == event.tenant_id,
                        WebhookDelivery.destination_id == subscription.destination_id,
                        WebhookDelivery.integration_event_id == event.id,
                    )
                )
                if existing is not None:
                    deliveries.append(existing)
                else:
                    raise
        return deliveries

    @staticmethod
    def _matches_filter(payload: dict[str, Any] | None, filter_config: dict[str, Any] | None) -> bool:
        if not filter_config:
            return True
        if not isinstance(filter_config, dict) or not isinstance(payload, dict):
            return False
        return all(key in payload and payload[key] == expected for key, expected in filter_config.items())


__all__ = ["NotificationRoutingService"]
