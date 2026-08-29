"""Runtime 时间序列维度采样服务。

职责：从 Durable Integration Event 与 Webhook Delivery facts 生成 Provider、Destination、Event Type 三维时间序列样本。
边界：只读取已经持久化的业务事实并写入 RuntimeMetricSample，不重新计算或修改 Delivery 状态；Provider 维度使用稳定的规范名称。
""" 

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.models.runtime_operations import RuntimeMetricSample
from app.models.webhook_delivery import WebhookDelivery


class RuntimeDimensionSampler:
    """从 Durable Delivery facts 生成可查询的三维时间序列样本。"""

    PROVIDER_WEBHOOK_HTTP = "webhook_http"
    METRIC_TOTAL = "runtime.delivery.total"
    METRIC_SUCCESS_PERCENT = "runtime.delivery.success_percent"
    METRIC_RETRY_COUNT = "runtime.delivery.retry_count"
    METRIC_DEAD_LETTER_COUNT = "runtime.delivery.dead_letter_count"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sample(self, tenant_id: UUID, *, window_hours: int = 24) -> int:
        """采样当前租户最近窗口内的 Provider/Destination/Event Type 指标。

        Args:
            tenant_id: 目标租户标识，所有读取和写入均严格限定在该租户。
            window_hours: 统计窗口，限制为 1 至 168 小时。

        Returns:
            本轮写入的时间序列样本数量。

        设计意图：时间序列是 Durable facts 的派生视图，因此每次采样都直接从事件与 Delivery
        持久化事实聚合，避免维护第二套业务状态；同一时间窗口内重复采样不会改变业务事实。
        """
        hours = min(max(window_hours, 1), 168)
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)
        rows = (await self.db.execute(
            select(
                IntegrationEventRecord.event_type,
                WebhookDelivery.destination_id,
                WebhookDelivery.status,
                func.count(),
            )
            .join(IntegrationEventRecord, IntegrationEventRecord.id == WebhookDelivery.integration_event_id)
            .where(
                WebhookDelivery.tenant_id == tenant_id,
                IntegrationEventRecord.tenant_id == tenant_id,
                WebhookDelivery.created_at >= since,
            )
            .group_by(
                IntegrationEventRecord.event_type,
                WebhookDelivery.destination_id,
                WebhookDelivery.status,
            )
        )).all()

        buckets: dict[tuple[str, UUID], dict[str, int]] = {}
        for event_type, destination_id, status, count in rows:
            buckets.setdefault((event_type, destination_id), {})[status] = int(count)

        attempt_rows = (await self.db.execute(
            select(
                IntegrationEventRecord.event_type,
                WebhookDelivery.destination_id,
                func.count(),
            )
            .join(IntegrationEventRecord, IntegrationEventRecord.id == WebhookDelivery.integration_event_id)
            .where(
                WebhookDelivery.tenant_id == tenant_id,
                IntegrationEventRecord.tenant_id == tenant_id,
                WebhookDelivery.created_at >= since,
                WebhookDelivery.attempt_count > 1,
            )
            .group_by(IntegrationEventRecord.event_type, WebhookDelivery.destination_id)
        )).all()
        retries = {(event_type, destination_id): int(count) for event_type, destination_id, count in attempt_rows}

        now = datetime.now(UTC).replace(tzinfo=None)
        samples: list[RuntimeMetricSample] = []
        for (event_type, destination_id), counts in buckets.items():
            delivered = counts.get("delivered", 0)
            terminal = delivered + counts.get("failed", 0) + counts.get("dead_letter", 0)
            success_percent = delivered / terminal * 100.0 if terminal else 100.0
            dimensions: dict[str, Any] = {
                "provider": self.PROVIDER_WEBHOOK_HTTP,
                "destination_id": str(destination_id),
                "event_type": event_type,
            }
            values = {
                self.METRIC_TOTAL: float(sum(counts.values())),
                self.METRIC_SUCCESS_PERCENT: round(success_percent, 4),
                self.METRIC_RETRY_COUNT: float(retries.get((event_type, destination_id), 0)),
                self.METRIC_DEAD_LETTER_COUNT: float(counts.get("dead_letter", 0)),
            }
            samples.extend(
                RuntimeMetricSample(
                    tenant_id=tenant_id,
                    metric_name=name,
                    value=value,
                    dimensions=dimensions,
                    recorded_at=now,
                )
                for name, value in values.items()
            )

        if samples:
            self.db.add_all(samples)
            await self.db.flush()
        return len(samples)
