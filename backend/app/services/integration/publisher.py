"""Runtime Integration Event 发布器。

职责：为 Workflow、Agent、Scheduler 等运行时领域提供统一的事务内事件写入入口。
边界：只负责构造/持久化 IntegrationEvent，不负责提交数据库事务、不负责 Webhook 投递。
设计原则：事件写入必须与产生业务事实的数据库事务共存；事件重复生产使用稳定幂等键收敛。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.services.integration.contract import IntegrationEvent
from app.services.integration.repository import IntegrationEventRepository


class RuntimeIntegrationEventPublisher:
    """提供 Runtime -> Durable Integration Event 的事务内发布能力。"""

    SOURCE_WORKFLOW = "workflow-runtime"
    SOURCE_AGENT = "agent-runtime"
    SOURCE_SCHEDULER = "scheduler-runtime"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = IntegrationEventRepository()

    async def publish(
        self,
        *,
        tenant_id: uuid.UUID,
        event_type: str,
        source: str,
        subject: str,
        idempotency_key: str,
        payload: dict[str, Any],
        request_id: str | None = None,
        trace_id: str | None = None,
        occurred_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IntegrationEventRecord:
        """在当前事务中幂等写入一个 Runtime Integration Event。

        调用方负责最终 commit/rollback；事件不会自行提交业务事务。
        """
        event = IntegrationEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            subject=subject,
            idempotency_key=idempotency_key,
            payload=payload,
            request_id=request_id,
            trace_id=trace_id,
            occurred_at=occurred_at or datetime.now(UTC),
            metadata=metadata or {},
        )
        try:
            async with self.db.begin_nested():
                record = await self.repository.create(self.db, event)
            return record
        except IntegrityError:
            # 唯一约束冲突只能代表同一租户/来源/事件类型/幂等键已被生产。
            # 使用 savepoint 后查询不会破坏外层业务事务。
            result = await self.db.execute(
                select(IntegrationEventRecord).where(
                    IntegrationEventRecord.tenant_id == tenant_id,
                    IntegrationEventRecord.source == source,
                    IntegrationEventRecord.event_type == event_type,
                    IntegrationEventRecord.idempotency_key == idempotency_key,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                raise
            return existing


__all__ = ["RuntimeIntegrationEventPublisher"]
