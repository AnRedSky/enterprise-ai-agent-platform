"""Runtime Notification Routing 周期调度。

职责：周期发现 tenant-scoped Durable Integration Events，并把匹配事件物化为
Webhook Delivery Facts。网络发送、重试、lease 与 dead-letter 继续由 Webhook
Delivery Worker 负责。

边界：不直接执行外部 HTTP；不修改 Integration Event 状态机；每个 tenant 使用
独立数据库事务，避免跨租户事务耦合。
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.integration_event import IntegrationEventRecord
from app.services.integration.notification_dispatcher import NotificationDispatcher

logger = logging.getLogger(__name__)


class RuntimeNotificationScheduler:
    """按租户周期执行 Durable Event -> Delivery Fact 路由。"""

    def __init__(self, poll_interval_seconds: float = 60.0, *, batch_size: int = 100):
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds 必须大于 0")
        if batch_size < 1 or batch_size > 1000:
            raise ValueError("batch_size 必须在 1 到 1000 之间")
        self.poll_interval_seconds = poll_interval_seconds
        self.batch_size = batch_size
        self._stop_event = asyncio.Event()

    async def tick_once(self) -> dict[str, int]:
        """发现存在待路由 Durable Event 的租户并逐租户物化 Delivery Facts。"""
        async with SessionLocal() as discovery_db:
            result = await discovery_db.execute(
                select(IntegrationEventRecord.tenant_id)
                .where(IntegrationEventRecord.status == "pending")
                .distinct()
            )
            tenant_ids: list[UUID] = list(result.scalars().all())

        created = 0
        for tenant_id in tenant_ids:
            async with SessionLocal() as db:
                try:
                    created += await NotificationDispatcher(
                        db, batch_size=self.batch_size
                    ).dispatch_tenant(tenant_id)
                    await db.commit()
                except Exception:
                    await db.rollback()
                    logger.exception("Notification routing failed for tenant %s", tenant_id)
                    raise
        return {"discovered": len(tenant_ids), "created": created}

    async def run_forever(self) -> None:
        """持续运行通知路由周期任务直到收到停止请求。"""
        while not self._stop_event.is_set():
            await self.tick_once()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        """请求停止周期任务。"""
        self._stop_event.set()
