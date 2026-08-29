"""Webhook Delivery Worker orchestration.

职责：领取 Webhook Delivery Fact、解析目标配置、执行 Provider 投递并完成 lease/retry 状态机。
边界：不创建调度计划；不管理 Destination/Subscription；不直接暴露 HTTP API。
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.infrastructure.db import SessionLocal
from app.models.webhook_delivery import WebhookDelivery
from app.services.integration.webhook_delivery_repository import WebhookDeliveryRepository


Sender = Callable[[WebhookDelivery, dict[str, Any]], Awaitable[int]]


class WebhookDeliveryWorker:
    """基于 PostgreSQL lease 的可恢复 Webhook Delivery Worker。"""

    def __init__(
        self,
        repository: WebhookDeliveryRepository | None = None,
        owner: str | None = None,
        sender: Sender | None = None,
        lease_seconds: int = 60,
        max_attempts: int = 5,
    ) -> None:
        self.repository = repository or WebhookDeliveryRepository()
        self.owner = owner or f"webhook-worker-{uuid.uuid4().hex}"
        self.sender = sender
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts
        self._running = True

    @staticmethod
    def retry_at(now: datetime, attempt_count: int, base_seconds: int = 2, max_seconds: int = 300) -> datetime:
        if attempt_count <= 0 or base_seconds <= 0 or max_seconds <= 0:
            raise ValueError("attempt_count、base_seconds、max_seconds 必须大于 0")
        return now + timedelta(seconds=min(max_seconds, base_seconds * (2 ** (attempt_count - 1))))

    async def deliver_once(self) -> bool:
        """领取并投递一个 Delivery Fact；没有可领取任务返回 False。"""
        if self.sender is None:
            raise RuntimeError("WebhookDeliveryWorker 未配置 sender")
        now = datetime.now(UTC).replace(tzinfo=None)
        async with SessionLocal() as db:
            record = await self.repository.claim_next(
                db, now, self.owner, self.lease_seconds, self.max_attempts
            )
            if record is None:
                return False
            await db.commit()
            delivery_id = record.id
            attempt_count = record.attempt_count
            payload = dict(record.integration_event.payload)
            destination = {
                "url": record.destination.endpoint_url,
                "headers": dict(record.destination.headers or {}),
                "secret_ref": record.destination.secret_ref,
            }

        try:
            status_code = await self.sender(record, {"payload": payload, "destination": destination})
        except Exception as exc:  # noqa: BLE001
            retry_at = self.retry_at(now, attempt_count) if attempt_count < self.max_attempts else None
            async with SessionLocal() as db:
                updated = await self.repository.mark_failed(
                    db, delivery_id, self.owner, datetime.now(UTC).replace(tzinfo=None),
                    type(exc).__name__, str(exc), retry_at,
                )
                await db.commit()
            return updated

        async with SessionLocal() as db:
            updated = await self.repository.mark_delivered(
                db, delivery_id, self.owner, datetime.now(UTC).replace(tzinfo=None), status_code
            )
            await db.commit()
        return updated

    def stop(self) -> None:
        """请求 Worker 停止。"""
        self._running = False

    async def run_forever(self, poll_interval: float = 0.2) -> None:
        """持续消费 Webhook Delivery Fact。"""
        import asyncio

        if poll_interval <= 0:
            raise ValueError("poll_interval 必须大于 0")
        while self._running:
            consumed = await self.deliver_once()
            if not consumed:
                await asyncio.sleep(poll_interval)
