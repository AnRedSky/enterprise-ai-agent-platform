"""Runtime Integration Event 运维聚合服务。

职责：在 tenant scope 内计算事件、Delivery、Notification、死信和 SLO 指标，并提供死信分页、维度指标与告警查询。
边界：只读查询；Replay、状态变更和网络投递必须继续通过正式领域 Repository / Worker 完成。
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.models.runtime_operations import RuntimeNotificationDelivery
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_integration import WebhookDestination


class RuntimeOperationsService:
    """提供租户隔离的 Runtime 运维指标与死信查询。"""

    PROVIDER_WEBHOOK_HTTP = "webhook_http"
    SLO_TARGET_PERCENT = 99.0

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _page(page: int, page_size: int) -> tuple[int, int, int]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        return page, page_size, (page - 1) * page_size

    @staticmethod
    def _since(window_hours: int) -> tuple[int, datetime]:
        window_hours = min(max(window_hours, 1), 168)
        return window_hours, datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=window_hours)

    @classmethod
    def _slo(cls, delivered: int, terminal: int) -> dict[str, float | None]:
        success_rate = (delivered / terminal * 100.0) if terminal else 100.0
        allowed_error_percent = 100.0 - cls.SLO_TARGET_PERCENT
        observed_error_percent = 100.0 - success_rate
        return {
            "target_percent": cls.SLO_TARGET_PERCENT,
            "delivery_success_percent": round(success_rate, 4),
            "error_budget_percent": round(max(0.0, allowed_error_percent - observed_error_percent), 4),
        }

    async def _notification_summary(self, tenant_id: UUID, since: datetime) -> dict[str, Any]:
        rows = (await self.db.execute(
            select(RuntimeNotificationDelivery.status, func.count())
            .where(RuntimeNotificationDelivery.tenant_id == tenant_id, RuntimeNotificationDelivery.created_at >= since)
            .group_by(RuntimeNotificationDelivery.status)
        )).all()
        status_counts = {status: count for status, count in rows}
        delivered = status_counts.get("delivered", 0)
        terminal = delivered + status_counts.get("failed", 0) + status_counts.get("dead_letter", 0)
        return {
            "total": sum(status_counts.values()),
            "status_counts": status_counts,
            "retry_count": status_counts.get("retrying", 0),
            "dead_letter_count": status_counts.get("dead_letter", 0),
            "slo": self._slo(delivered, terminal),
        }

    async def overview(self, tenant_id: UUID, *, window_hours: int = 24) -> dict[str, Any]:
        """计算当前租户的事件、Delivery、Notification、死信与双层 SLO 运维摘要。"""
        window_hours, since = self._since(window_hours)
        event_base = select(IntegrationEventRecord.status, func.count()).where(
            IntegrationEventRecord.tenant_id == tenant_id, IntegrationEventRecord.created_at >= since,
        ).group_by(IntegrationEventRecord.status)
        event_counts = {status: count for status, count in (await self.db.execute(event_base)).all()}
        delivery_base = select(WebhookDelivery.status, func.count()).where(
            WebhookDelivery.tenant_id == tenant_id, WebhookDelivery.created_at >= since,
        ).group_by(WebhookDelivery.status)
        delivery_counts = {status: count for status, count in (await self.db.execute(delivery_base)).all()}
        total_deliveries = sum(delivery_counts.values())
        delivered = delivery_counts.get("delivered", 0)
        terminal = delivered + delivery_counts.get("failed", 0) + delivery_counts.get("dead_letter", 0)
        retry_count = await self.db.scalar(select(func.count()).select_from(WebhookDelivery).where(
            WebhookDelivery.tenant_id == tenant_id, WebhookDelivery.created_at >= since,
            WebhookDelivery.attempt_count > 1,
        )) or 0
        latency_ms = await self.db.scalar(select(
            func.percentile_cont(0.95).within_group(
                func.extract("epoch", WebhookDelivery.delivered_at - WebhookDelivery.created_at) * 1000
            )
        ).where(
            WebhookDelivery.tenant_id == tenant_id, WebhookDelivery.created_at >= since,
            WebhookDelivery.status == "delivered", WebhookDelivery.delivered_at.is_not(None),
        ))
        slo = self._slo(delivered, terminal)
        slo["p95_delivery_latency_ms"] = round(float(latency_ms), 2) if latency_ms is not None else None
        notification = await self._notification_summary(tenant_id, since)
        return {
            "window_hours": window_hours, "since": since, "generated_at": datetime.now(UTC),
            "events": {"total": sum(event_counts.values()), "status_counts": event_counts},
            "deliveries": {"total": total_deliveries, "status_counts": delivery_counts,
                           "retry_count": retry_count, "dead_letter_count": delivery_counts.get("dead_letter", 0)},
            "slo": slo,
            "notifications": notification,
        }

    async def notification_metrics(self, tenant_id: UUID, *, window_hours: int = 24) -> dict[str, Any]:
        """聚合 Alert -> Notification -> Provider -> Destination 的租户级运行指标。"""
        window_hours, since = self._since(window_hours)
        rows = (await self.db.execute(
            select(
                RuntimeNotificationDelivery.provider,
                RuntimeNotificationDelivery.transition,
                RuntimeNotificationDelivery.status,
                WebhookDelivery.destination_id,
                WebhookDestination.name,
                func.count(),
            ).join(
                WebhookDelivery,
                WebhookDelivery.id == RuntimeNotificationDelivery.webhook_delivery_id,
            ).join(
                WebhookDestination,
                WebhookDestination.id == WebhookDelivery.destination_id,
            ).where(
                RuntimeNotificationDelivery.tenant_id == tenant_id,
                WebhookDelivery.tenant_id == tenant_id,
                WebhookDestination.tenant_id == tenant_id,
                RuntimeNotificationDelivery.created_at >= since,
            ).group_by(
                RuntimeNotificationDelivery.provider,
                RuntimeNotificationDelivery.transition,
                RuntimeNotificationDelivery.status,
                WebhookDelivery.destination_id,
                WebhookDestination.name,
            )
        )).all()
        items = [
            {
                "provider": provider or "unknown",
                "transition": transition,
                "status": status,
                "destination_id": destination_id,
                "destination_name": destination_name,
                "count": count,
            }
            for provider, transition, status, destination_id, destination_name, count in rows
        ]
        items.sort(key=lambda item: (item["provider"], item["transition"], item["status"] or "", str(item["destination_id"])))
        return {"window_hours": window_hours, "since": since, "generated_at": datetime.now(UTC), "items": items}

    async def dimension_metrics(self, tenant_id: UUID, *, window_hours: int = 24) -> dict[str, Any]:
        """按 Event Type、Destination 和当前 HTTP Provider 聚合 Durable Delivery facts。"""
        window_hours, since = self._since(window_hours)
        rows = (await self.db.execute(
            select(
                IntegrationEventRecord.event_type,
                WebhookDelivery.destination_id,
                WebhookDelivery.status,
                func.count(),
            ).join(
                IntegrationEventRecord, IntegrationEventRecord.id == WebhookDelivery.integration_event_id,
            ).where(
                WebhookDelivery.tenant_id == tenant_id,
                IntegrationEventRecord.tenant_id == tenant_id,
                WebhookDelivery.created_at >= since,
            ).group_by(
                IntegrationEventRecord.event_type, WebhookDelivery.destination_id, WebhookDelivery.status,
            )
        )).all()
        destination_ids = {destination_id for _, destination_id, _, _ in rows}
        names: dict[UUID, str] = {}
        if destination_ids:
            names = dict((await self.db.execute(
                select(WebhookDestination.id, WebhookDestination.name).where(
                    WebhookDestination.tenant_id == tenant_id, WebhookDestination.id.in_(destination_ids)
                )
            )).all())
        buckets: dict[tuple[str, UUID], dict[str, int]] = {}
        for event_type, destination_id, status, count in rows:
            buckets.setdefault((event_type, destination_id), {})[status] = count
        dimensions = []
        for (event_type, destination_id), counts in buckets.items():
            delivered = counts.get("delivered", 0)
            terminal = delivered + counts.get("failed", 0) + counts.get("dead_letter", 0)
            slo = self._slo(delivered, terminal)
            dimensions.append({
                "event_type": event_type, "provider": self.PROVIDER_WEBHOOK_HTTP,
                "destination_id": destination_id, "destination_name": names.get(destination_id),
                "total": sum(counts.values()), "status_counts": counts,
                "retry_count": counts.get("retry", 0), "dead_letter_count": counts.get("dead_letter", 0),
                "delivery_success_percent": slo["delivery_success_percent"],
            })
        dimensions.sort(key=lambda item: (item["event_type"], str(item["destination_id"])))
        return {"window_hours": window_hours, "since": since, "generated_at": datetime.now(UTC), "items": dimensions}

    async def alerts(self, tenant_id: UUID, *, window_hours: int = 24) -> dict[str, Any]:
        """根据 Durable facts 评估固定、可解释的 Runtime 运维告警。"""
        overview = await self.overview(tenant_id, window_hours=window_hours)
        slo = overview["slo"]
        notifications = overview["notifications"]
        deliveries = overview["deliveries"]
        alerts: list[dict[str, Any]] = []
        success = float(slo["delivery_success_percent"])
        if success < self.SLO_TARGET_PERCENT:
            alerts.append({"code": "delivery_slo_breach", "severity": "critical", "message": "Delivery success rate is below the 99% SLO."})
        notification_success = float(notifications["slo"]["delivery_success_percent"])
        if notification_success < self.SLO_TARGET_PERCENT:
            alerts.append({"code": "notification_slo_breach", "severity": "critical", "message": "Notification delivery success rate is below the 99% SLO."})
        if deliveries["dead_letter_count"] > 0 or notifications["dead_letter_count"] > 0:
            alerts.append({"code": "dead_letter_present", "severity": "warning", "message": "One or more deliveries are in dead letter state."})
        if deliveries["retry_count"] > 0 or notifications["retry_count"] > 0:
            alerts.append({"code": "delivery_retry_present", "severity": "info", "message": "One or more deliveries required retry."})
        return {"window_hours": overview["window_hours"], "generated_at": datetime.now(UTC), "items": alerts}

    async def dead_letters(self, tenant_id: UUID, *, page: int = 1, page_size: int = 20) -> tuple[int, int, int, list[WebhookDelivery]]:
        """分页查询当前租户死信 Delivery，不执行任何状态变更。"""
        page, page_size, offset = self._page(page, page_size)
        stmt = select(WebhookDelivery).where(WebhookDelivery.tenant_id == tenant_id, WebhookDelivery.status == "dead_letter")
        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = (await self.db.execute(
            stmt.order_by(WebhookDelivery.updated_at.desc(), WebhookDelivery.id.desc()).offset(offset).limit(page_size)
        )).scalars().all()
        return page, page_size, total, rows
