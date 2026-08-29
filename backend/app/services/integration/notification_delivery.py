"""Idempotent alert notification -> durable delivery routing."""

from __future__ import annotations

import hashlib
import uuid
from typing import Sequence

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
        material = f"{event.tenant_id}:{event.event_type}:{event.id}:{subscription.destination_id}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    async def dispatch_event(
        self,
        event: IntegrationEventRecord,
        *,
        destination_ids: Sequence[uuid.UUID] | None = None,
        provider_order: Sequence[str] | None = None,
        fallback: bool = False,
    ) -> list[WebhookDelivery]:
        """Route to policy-selected destinations with deterministic provider ordering.

        When ``fallback`` is true only the first enabled destination for the first
        available provider is materialized. Callers can invoke this again after a
        terminal delivery failure to advance to the next provider tier.
        """
        query = (
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
        )
        if destination_ids:
            query = query.where(WebhookDestination.id.in_(list(destination_ids)))
        result = await self.db.execute(query)
        subscriptions = [
            subscription for subscription in result.scalars().all()
            if NotificationRoutingService._matches_filter(event.payload, subscription.filter_config)
        ]

        if provider_order:
            order = {provider: index for index, provider in enumerate(provider_order)}
            destinations = {
                subscription.destination_id: subscription
                for subscription in subscriptions
            }
            destination_rows = await self.db.execute(
                select(WebhookDestination).where(WebhookDestination.id.in_(list(destinations)))
            )
            provider_by_destination = {row.id: row.provider for row in destination_rows.scalars().all()}
            subscriptions.sort(key=lambda item: (order.get(provider_by_destination.get(item.destination_id, ""), len(order)), item.priority, item.id))

        if fallback and subscriptions:
            first_provider = None
            selected = []
            for subscription in subscriptions:
                destination_provider = await self.db.scalar(
                    select(WebhookDestination.provider).where(WebhookDestination.id == subscription.destination_id)
                )
                if first_provider is None:
                    first_provider = destination_provider
                if destination_provider == first_provider:
                    selected.append(subscription)
                    break
            subscriptions = selected

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
        await self.db.execute(
            pg_insert(WebhookDelivery).values(values).on_conflict_do_nothing(
                constraint="uq_webhook_delivery_event_destination"
            )
        )
        await self.db.flush()
        return list((await self.db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.tenant_id == event.tenant_id,
                WebhookDelivery.integration_event_id == event.id,
                WebhookDelivery.destination_id.in_([s.destination_id for s in subscriptions]),
            ).order_by(WebhookDelivery.created_at, WebhookDelivery.id)
        )).scalars().all())


__all__ = ["AlertNotificationDeliveryService"]
