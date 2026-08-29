"""Webhook Destination / Subscription / Fan-out orchestration.

该服务只负责 tenant-scoped 配置管理与 Delivery Fact 规划，不执行 HTTP 请求。
真实网络投递由后续 Webhook Delivery Worker + Provider 完成。
"""

from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_integration import WebhookDestination, WebhookSubscription


class WebhookIntegrationService:
    """管理 Destination / Subscription，并将 Event fan-out 成独立 Delivery Fact。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_destination(
        self,
        tenant_id: uuid.UUID,
        name: str,
        endpoint_url: str,
        secret_ref: str | None = None,
        headers: dict | None = None,
    ) -> WebhookDestination:
        item = WebhookDestination(
            tenant_id=tenant_id,
            name=name,
            endpoint_url=endpoint_url,
            secret_ref=secret_ref,
            headers=headers or {},
            enabled=True,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def list_destinations(self, tenant_id: uuid.UUID) -> list[WebhookDestination]:
        result = await self.db.execute(
            select(WebhookDestination)
            .where(WebhookDestination.tenant_id == tenant_id)
            .order_by(WebhookDestination.created_at, WebhookDestination.id)
        )
        return list(result.scalars().all())

    async def create_subscription(
        self,
        tenant_id: uuid.UUID,
        destination_id: uuid.UUID,
        event_type: str,
        priority: int = 100,
        filter_config: dict | None = None,
    ) -> WebhookSubscription:
        destination = await self.db.scalar(
            select(WebhookDestination).where(
                WebhookDestination.id == destination_id,
                WebhookDestination.tenant_id == tenant_id,
            )
        )
        if destination is None:
            raise ValueError("Destination 不存在或不属于当前租户")
        item = WebhookSubscription(
            tenant_id=tenant_id,
            destination_id=destination_id,
            event_type=event_type,
            priority=priority,
            enabled=True,
            filter_config=filter_config or {},
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def list_subscriptions(self, tenant_id: uuid.UUID) -> list[WebhookSubscription]:
        result = await self.db.execute(
            select(WebhookSubscription)
            .where(WebhookSubscription.tenant_id == tenant_id)
            .order_by(WebhookSubscription.priority, WebhookSubscription.created_at, WebhookSubscription.id)
        )
        return list(result.scalars().all())

    async def plan_fanout(self, tenant_id: uuid.UUID, event_id: uuid.UUID) -> int:
        """为一个 Durable Event 幂等规划所有匹配 Destination 的 Delivery Fact。"""
        event = await self.db.scalar(
            select(IntegrationEventRecord).where(
                IntegrationEventRecord.id == event_id,
                IntegrationEventRecord.tenant_id == tenant_id,
            )
        )
        if event is None:
            raise ValueError("Integration Event 不存在或不属于当前租户")

        result = await self.db.execute(
            select(WebhookSubscription)
            .join(WebhookDestination, WebhookDestination.id == WebhookSubscription.destination_id)
            .where(
                WebhookSubscription.tenant_id == tenant_id,
                WebhookSubscription.event_type == event.event_type,
                WebhookSubscription.enabled.is_(True),
                WebhookDestination.enabled.is_(True),
            )
            .order_by(WebhookSubscription.priority, WebhookSubscription.id)
        )
        subscriptions = list(result.scalars().all())
        if not subscriptions:
            return 0

        values = [
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
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
            .on_conflict_do_nothing(
                constraint="uq_webhook_delivery_event_destination"
            )
        )
        result = await self.db.execute(statement)
        await self.db.flush()
        return int(result.rowcount or 0)
