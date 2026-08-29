"""Runtime Integration Event 运维聚合服务。

职责：在 tenant scope 内计算事件、Delivery、死信和 SLO 指标，并提供死信分页查询。
边界：只读查询；Replay、状态变更和网络投递必须继续通过正式领域 Repository / Worker 完成。
关键依赖：SQLAlchemy AsyncSession、IntegrationEventRecord、WebhookDelivery。
"""

from datetime import datetime, timedelta, UTC
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.models.webhook_delivery import WebhookDelivery


class RuntimeOperationsService:
    """提供租户隔离的 Runtime 运维指标与死信查询。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _page(page: int, page_size: int) -> tuple[int, int, int]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        return page, page_size, (page - 1) * page_size

    async def overview(self, tenant_id: UUID, *, window_hours: int = 24) -> dict[str, Any]:
        """计算当前租户的事件、Delivery、死信与 SLO 运维摘要。

        Args:
            tenant_id: 当前认证上下文中的租户 ID。
            window_hours: 统计窗口，范围 1~168 小时。

        Returns:
            包含事件状态、Delivery 状态、成功率、重试率、死信率和 P95 投递延迟的聚合结果。
        """
        window_hours = min(max(window_hours, 1), 168)
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=window_hours)

        event_base = select(IntegrationEventRecord.status, func.count()).where(
            IntegrationEventRecord.tenant_id == tenant_id,
            IntegrationEventRecord.created_at >= since,
        ).group_by(IntegrationEventRecord.status)
        event_counts = {status: count for status, count in (await self.db.execute(event_base)).all()}

        delivery_base = select(WebhookDelivery.status, func.count()).where(
            WebhookDelivery.tenant_id == tenant_id,
            WebhookDelivery.created_at >= since,
        ).group_by(WebhookDelivery.status)
        delivery_counts = {status: count for status, count in (await self.db.execute(delivery_base)).all()}

        total_deliveries = sum(delivery_counts.values())
        delivered = delivery_counts.get("delivered", 0)
        terminal = delivered + delivery_counts.get("failed", 0) + delivery_counts.get("dead_letter", 0)
        retryable = await self.db.scalar(
            select(func.count()).select_from(WebhookDelivery).where(
                WebhookDelivery.tenant_id == tenant_id,
                WebhookDelivery.created_at >= since,
                WebhookDelivery.attempt_count > 1,
            )
        ) or 0
        latency_ms = await self.db.scalar(
            select(
                func.percentile_cont(0.95).within_group(
                    func.extract("epoch", WebhookDelivery.delivered_at - WebhookDelivery.created_at) * 1000
                )
            ).where(
                WebhookDelivery.tenant_id == tenant_id,
                WebhookDelivery.created_at >= since,
                WebhookDelivery.status == "delivered",
                WebhookDelivery.delivered_at.is_not(None),
            )
        )

        success_rate = (delivered / terminal * 100.0) if terminal else 100.0
        slo_target = 99.0
        error_budget = max(0.0, slo_target - (100.0 - success_rate))
        return {
            "window_hours": window_hours,
            "since": since,
            "generated_at": datetime.now(UTC),
            "events": {"total": sum(event_counts.values()), "status_counts": event_counts},
            "deliveries": {
                "total": total_deliveries,
                "status_counts": delivery_counts,
                "retry_count": retryable,
                "dead_letter_count": delivery_counts.get("dead_letter", 0),
            },
            "slo": {
                "target_percent": slo_target,
                "delivery_success_percent": round(success_rate, 4),
                "error_budget_percent": round(error_budget, 4),
                "p95_delivery_latency_ms": round(float(latency_ms), 2) if latency_ms is not None else None,
            },
        }

    async def dead_letters(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 20,
    ) -> tuple[int, int, int, list[WebhookDelivery]]:
        """分页查询当前租户死信 Delivery，不执行任何状态变更。

        Args:
            tenant_id: 当前认证上下文中的租户 ID。
            page: 从 1 开始的页码。
            page_size: 每页数量，最大 100。

        Returns:
            页码、页大小、总数以及按更新时间倒序排列的死信记录。
        """
        page, page_size, offset = self._page(page, page_size)
        stmt = select(WebhookDelivery).where(
            WebhookDelivery.tenant_id == tenant_id,
            WebhookDelivery.status == "dead_letter",
        )
        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = (await self.db.execute(
            stmt.order_by(WebhookDelivery.updated_at.desc(), WebhookDelivery.id.desc())
            .offset(offset).limit(page_size)
        )).scalars().all()
        return page, page_size, total, rows
