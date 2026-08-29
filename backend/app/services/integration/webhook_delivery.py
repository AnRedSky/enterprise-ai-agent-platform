"""Webhook Delivery Worker orchestration.

职责：领取 Webhook Delivery Fact、解析目标配置、执行 Provider 投递并完成 lease/retry 状态机，
同时把结果同步回 Alert Notification Runtime。
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
from app.services.integration.alert_lifecycle import AlertLifecycleService
from app.services.integration.webhook_delivery_repository import WebhookDeliveryRepository
from app.services.integration.webhook_provider import WebhookDeliveryHTTPError


Sender = Callable[[WebhookDelivery, dict[str, Any]], Awaitable[int]]


class WebhookDeliveryWorker:
    """基于 PostgreSQL lease 的可恢复 Webhook Delivery Worker。"""

    DEFAULT_CONCURRENCY = 4

    def __init__(
        self,
        repository: WebhookDeliveryRepository | None = None,
        owner: str | None = None,
        sender: Sender | None = None,
        lease_seconds: int = 60,
        max_attempts: int = 5,
        concurrency: int = DEFAULT_CONCURRENCY,
        tenant_id: uuid.UUID | None = None,
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
        self.tenant_id = tenant_id
        self._running = True

    @staticmethod
    def retry_at(now: datetime, attempt_count: int, base_seconds: int = 2, max_seconds: int = 300) -> datetime:
        if attempt_count <= 0 or base_seconds <= 0 or max_seconds <= 0:
            raise ValueError("attempt_count、base_seconds、max_seconds 必须大于 0")
        return now + timedelta(seconds=min(max_seconds, base_seconds * (2 ** (attempt_count - 1))))

    @staticmethod
    def _notification_status(delivery: WebhookDelivery, *, success: bool | None = None) -> str:
        """Translate durable webhook state into notification lifecycle semantics."""
        if success is True:
            return "delivered"
        if delivery.status == "dead_letter":
            return "dead_letter"
        if delivery.status in {"pending", "running"}:
            return "retrying"
        if delivery.status == "delivered":
            return "delivered"
        return "failed"

    async def _record_notification_outcome(
        self,
        delivery_id: uuid.UUID,
        status: str,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Persist notification outcome in its own transaction so Worker state is authoritative."""
        async with SessionLocal() as db:
            lifecycle = AlertLifecycleService(db, actor=self.owner)
            await lifecycle.record_delivery_outcome(
                delivery_id,
                status=status,
                error_code=error_code,
                error_message=error_message,
                now=datetime.now(UTC).replace(tzinfo=None),
            )
            await db.commit()

    async def deliver_once(self) -> bool:
        """领取并投递一个 Delivery Fact；同步 Notification Runtime 的结果。"""
        if self.sender is None:
            raise RuntimeError("WebhookDeliveryWorker 未配置 sender")
        now = datetime.now(UTC).replace(tzinfo=None)
        async with SessionLocal() as db:
            record = await self.repository.claim_next(
                db, now, self.owner, self.lease_seconds, self.max_attempts, self.tenant_id
            )
            if record is None:
                return False
            await db.commit()
            delivery_id = record.id
            attempt_count = record.attempt_count
            payload = dict(record.integration_event.payload)
            destination = {
                "provider": record.destination.provider,
                "url": record.destination.endpoint_url,
                "headers": dict(record.destination.headers or {}),
                "secret_ref": record.destination.secret_ref,
            }

        try:
            status_code = await self.sender(record, {"payload": payload, "destination": destination})
        except Exception as exc:  # noqa: BLE001
            retry_at = self.retry_at(now, attempt_count) if attempt_count < self.max_attempts else None
            response_status_code = exc.status_code if isinstance(exc, WebhookDeliveryHTTPError) else None
            error_code = type(exc).__name__
            error_message = str(exc)
            async with SessionLocal() as db:
                updated = await self.repository.mark_failed(
                    db, delivery_id, self.owner, datetime.now(UTC).replace(tzinfo=None),
                    error_code, error_message, retry_at, response_status_code,
                )
                delivery_state = await self.repository.get(db, record.tenant_id, delivery_id)
                await db.commit()
            if updated and delivery_state is not None:
                await self._record_notification_outcome(
                    delivery_id,
                    self._notification_status(delivery_state),
                    error_code=error_code,
                    error_message=error_message,
                )
            return updated

        async with SessionLocal() as db:
            updated = await self.repository.mark_delivered(
                db, delivery_id, self.owner, datetime.now(UTC).replace(tzinfo=None), status_code
            )
            delivery_state = await self.repository.get(db, record.tenant_id, delivery_id)
            await db.commit()
        if updated and delivery_state is not None:
            await self._record_notification_outcome(delivery_id, "delivered")
        return updated

    def stop(self) -> None:
        self._running = False

    async def run_forever(self, poll_interval: float = 0.2) -> None:
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
