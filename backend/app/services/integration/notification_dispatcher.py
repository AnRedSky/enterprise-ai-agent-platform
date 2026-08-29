"""Durable Integration Event -> Notification 路由批处理。

职责：处理通用 Integration Event 的订阅路由。
边界：`alert.*` 事件由 AlertLifecycleService 按 Notification Policy 独占路由，本模块禁止绕过
Policy 直接投递；实际网络发送继续由 WebhookDeliveryWorker 负责。
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.services.integration.notification import NotificationRoutingService


class NotificationDispatcher:
    """按租户批量物化通用 Integration Event Delivery Facts。"""

    def __init__(self, db: AsyncSession, *, batch_size: int = 100):
        if batch_size < 1 or batch_size > 1000:
            raise ValueError("batch_size must be between 1 and 1000")
        self.db = db
        self.batch_size = batch_size
        self.router = NotificationRoutingService(db)

    async def dispatch_tenant(self, tenant_id: uuid.UUID) -> int:
        """物化租户通用事件 Delivery Facts；Alert 事件由告警生命周期专用路由处理。"""
        result = await self.db.execute(
            select(IntegrationEventRecord)
            .where(
                IntegrationEventRecord.tenant_id == tenant_id,
                IntegrationEventRecord.status == "pending",
                ~IntegrationEventRecord.event_type.like("alert.%"),
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
