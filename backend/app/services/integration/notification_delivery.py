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
    """Materialize policy-selected, tenant-scoped webhook delivery facts."""
    SUPPORTED_PROVIDERS = frozenset({"webhook_http"})

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def notification_key(event: IntegrationEventRecord, subscription: WebhookSubscription) -> str:
        return hashlib.sha256(f"{event.tenant_id}:{event.event_type}:{event.id}:{subscription.destination_id}".encode()).hexdigest()

    async def dispatch_event(self, event: IntegrationEventRecord, *,
                             destination_ids: Sequence[uuid.UUID] | None = None,
                             provider_order: Sequence[str] | None = None,
                             fallback: bool = False,
                             exclude_providers: Sequence[str] | None = None) -> list[WebhookDelivery]:
        """Select destinations deterministically; fallback selects one provider tier."""
        query = select(WebhookSubscription).join(WebhookDestination, WebhookDestination.id == WebhookSubscription.destination_id).where(
            WebhookSubscription.tenant_id == event.tenant_id,
            WebhookSubscription.event_type == event.event_type,
            WebhookSubscription.enabled.is_(True),
            WebhookDestination.tenant_id == event.tenant_id,
            WebhookDestination.enabled.is_(True),
            WebhookDestination.provider.in_(self.SUPPORTED_PROVIDERS),
        )
        if destination_ids:
            query = query.where(WebhookDestination.id.in_(list(destination_ids)))
        if exclude_providers:
            query = query.where(~WebhookDestination.provider.in_(list(exclude_providers)))
        result = await self.db.execute(query)
        subscriptions = [s for s in result.scalars().all()
                         if NotificationRoutingService._matches_filter(event.payload, s.filter_config)]
        provider_by_destination: dict[uuid.UUID, str] = {}
        if subscriptions:
            rows = await self.db.execute(select(WebhookDestination).where(WebhookDestination.id.in_([s.destination_id for s in subscriptions])))
            provider_by_destination = {row.id: row.provider for row in rows.scalars().all()}
        if provider_order:
            order = {provider: index for index, provider in enumerate(provider_order)}
            subscriptions.sort(key=lambda s: (order.get(provider_by_destination.get(s.destination_id, ""), len(order)), s.priority, s.id))
        else:
            subscriptions.sort(key=lambda s: (s.priority, s.id))
        if fallback and subscriptions:
            selected_provider = provider_by_destination.get(subscriptions[0].destination_id)
            subscriptions = [s for s in subscriptions if provider_by_destination.get(s.destination_id) == selected_provider][:1]
        if not subscriptions:
            return []
        values = [{"id": uuid.uuid4(), "tenant_id": event.tenant_id, "subscription_id": s.id,
                   "destination_id": s.destination_id, "integration_event_id": event.id,
                   "status": "pending", "attempt_count": 0} for s in subscriptions]
        await self.db.execute(pg_insert(WebhookDelivery).values(values).on_conflict_do_nothing(constraint="uq_webhook_delivery_event_destination"))
        await self.db.flush()
        return list((await self.db.execute(select(WebhookDelivery).where(
            WebhookDelivery.tenant_id == event.tenant_id,
            WebhookDelivery.integration_event_id == event.id,
            WebhookDelivery.destination_id.in_([s.destination_id for s in subscriptions]),
        ).order_by(WebhookDelivery.created_at, WebhookDelivery.id))).scalars().all())


__all__ = ["AlertNotificationDeliveryService"]
