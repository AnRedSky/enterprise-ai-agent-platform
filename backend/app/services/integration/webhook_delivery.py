"""Webhook Delivery Worker orchestration.

职责：领取 Webhook Delivery Fact、解析目标配置、执行 Provider 投递并完成 lease/retry 状态机。
边界：不创建调度计划；不管理 Destination/Subscription；不直接暴露 HTTP API。
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.infrastructure.db import SessionLocal
from app.models.webhook_delivery import WebhookDelivery
from app.services.integration.webhook_delivery_repository import WebhookDeliveryRepository


Sender = Callable[[WebhookDelivery, dict[str, Any]], Awaitable[int]]


class WebhookDeliveryWorker:
    """基于 PostgreSQL lease 的可恢复 Webhook Delivery Worker。

    `concurrency` 是单进程最大 in-flight delivery 数，也是 backpressure 边界。
    Worker 不建立无界任务队列：只有存在空闲执行槽时才会继续 Claim。
    """

    DEFAULT_CONCURRENCY = 4

    def __init__(
        self,
        repository: WebhookDeliveryRepository | None = None,
        owner: str | None = None,
        sender: Sender | None = None,
        lease_seconds: int = 60,
        max_attempts: int = 5,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds 必须大于 0")
        if max_attempts <= 0:
            raise ValueError("max_attempts 必须大于 0")
        if concurrency <= 0:
            raise ValueError("concurrency 必须大于 0")
        self.repository = repository or WebhookDeliveryRepository()
        self.owner = owner or f"webhook-worker-{uuid.uuid4().hex}"
        self.sender = sender
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts
        self.concurrency = concurrency
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
        """请求 Worker 停止；已有 in-flight delivery 会在 graceful shutdown 中完成。"""
        self._running = False

    async def run_forever(self, poll_interval: float = 0.2) -> None:
        """并发消费 Webhook Delivery Fact，并在停止时等待已领取任务完成。

        backpressure 通过 `concurrency` 实现：任务集合永远不超过该上限。
        stop() 后不再 Claim 新任务，但会 drain 已经领取的任务，避免把 lease 中任务
        在正常退出时无谓地留给下一轮恢复。
        """
        if poll_interval <= 0:
            raise ValueError("poll_interval 必须大于 0")

        tasks: set[asyncio.Task[bool]] = set()
        try:
            while self._running or tasks:
                while self._running and len(tasks) < self.concurrency:
                    tasks.add(asyncio.create_task(self.deliver_once()))

                if not tasks:
                    break

                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                tasks = set(pending)
                idle = False
                for task in done:
                    if not task.result():
                        idle = True
                if idle and self._running:
                    await asyncio.sleep(poll_interval)
        finally:
            if tasks:
                await asyncio.gather(*tasks)
