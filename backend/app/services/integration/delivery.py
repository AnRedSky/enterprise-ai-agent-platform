"""Integration Event 可靠投递策略。

职责：编排 Durable Event Claim、发送器调用、有限重试和 dead-letter。
边界：不实现具体 Webhook/消息中间件客户端；发送器由调用方注入。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.database import SessionLocal
from app.services.integration.repository import IntegrationEventRepository

Sender = Callable[[Any], Awaitable[None]]


class IntegrationEventDeliveryService:
    """基于 PostgreSQL Durable Event 实现可恢复、幂等的投递编排。"""

    def __init__(self, repository: IntegrationEventRepository | None = None) -> None:
        """创建投递服务并注入 Repository。"""
        self.repository = repository or IntegrationEventRepository()

    @staticmethod
    def retry_at(now: datetime, attempt_count: int, base_seconds: int = 2, max_seconds: int = 300) -> datetime:
        """计算指数退避时间，避免失败事件持续占用 Worker。

        Args:
            now: 当前 UTC 时间。
            attempt_count: 本次失败后的累计尝试次数。
            base_seconds: 第一次重试的基础等待秒数。
            max_seconds: 最大退避秒数。
        Returns:
            下一次允许投递的时间。
        Raises:
            ValueError: 参数不是正数。
        """
        if attempt_count <= 0 or base_seconds <= 0 or max_seconds <= 0:
            raise ValueError("attempt_count、base_seconds、max_seconds 必须大于 0")
        delay = min(max_seconds, base_seconds * (2 ** (attempt_count - 1)))
        return now + timedelta(seconds=delay)

    async def deliver_once(
        self, tenant_id, owner: str, sender: Sender,
        lease_seconds: int = 60, max_attempts: int = 5,
    ) -> bool:
        """领取并尝试投递一个事件；Claim 与发送结果更新使用独立事务边界。

        Args:
            tenant_id: 目标租户标识。
            owner: 当前 Worker 唯一标识。
            sender: 具体外部发送器异步函数。
            lease_seconds: 事件租约秒数。
            max_attempts: 最大投递次数。
        Returns:
            ``True`` 表示领取并处理了一个事件，``False`` 表示当前没有可领取事件。
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        async with SessionLocal() as db:
            record = await self.repository.claim_next(db, tenant_id, owner, now, lease_seconds, max_attempts)
            if record is None:
                return False
            await db.commit()
            event_id = record.id
            attempt_count = record.attempt_count
            payload = record.payload
        try:
            await sender(payload)
        except Exception as exc:  # noqa: BLE001
            retry_at = self.retry_at(now, attempt_count) if attempt_count < max_attempts else None
            async with SessionLocal() as db:
                await self.repository.mark_failed(
                    db, event_id, owner, datetime.now(UTC).replace(tzinfo=None),
                    type(exc).__name__, str(exc), retry_at,
                )
                await db.commit()
        else:
            async with SessionLocal() as db:
                await self.repository.mark_delivered(
                    db, event_id, owner, datetime.now(UTC).replace(tzinfo=None)
                )
                await db.commit()
        return True
