"""Runtime 运维企业扩展服务。

职责：提供 Provider/Destination 注册查询、告警规则管理、时间序列样本、Prometheus/OpenTelemetry 导出与运维审计。
边界：Provider 注册只保存适配器元数据；Destination 复用既有 WebhookDestination；指标仍从 Durable facts 计算。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.runtime_operations import RuntimeAlertRule, RuntimeMetricSample, RuntimeOperationAudit, RuntimeProviderRegistry
from app.models.webhook_integration import WebhookDestination
from app.services.runtime_operations.service import RuntimeOperationsService


class RuntimeOperationsEnterpriseService:
    """提供 2.10-I 的持久化注册、时间序列、导出和审计能力。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.metrics = RuntimeOperationsService(db)

    async def providers(self, tenant_id: UUID) -> list[RuntimeProviderRegistry]:
        """查询当前租户 Provider 注册表。"""
        return list((await self.db.execute(select(RuntimeProviderRegistry).where(RuntimeProviderRegistry.tenant_id == tenant_id).order_by(RuntimeProviderRegistry.name))).scalars().all())

    async def create_provider(self, tenant_id: UUID, name: str, provider_type: str, config: dict, actor: str) -> RuntimeProviderRegistry:
        """创建 Provider 注册；config 仅允许非敏感元数据和 Secret 引用。"""
        forbidden = {"api_key", "apikey", "token", "password", "secret", "secret_value"}
        if any(key.lower() in forbidden for key in config):
            raise ValueError("provider config must not contain raw secrets")
        item = RuntimeProviderRegistry(tenant_id=tenant_id, name=name, provider_type=provider_type, config=config, enabled=True)
        self.db.add(item)
        await self.db.flush()
        await self.audit(tenant_id, actor, "provider.create", "provider", str(item.id), "success", {"name": name, "provider_type": provider_type})
        return item

    async def destinations(self, tenant_id: UUID) -> list[WebhookDestination]:
        """查询当前租户的正式 Webhook Destination 注册信息。"""
        return list((await self.db.execute(select(WebhookDestination).where(WebhookDestination.tenant_id == tenant_id).order_by(WebhookDestination.name))).scalars().all())

    async def alerts_rules(self, tenant_id: UUID) -> list[RuntimeAlertRule]:
        """查询当前租户告警规则。"""
        return list((await self.db.execute(select(RuntimeAlertRule).where(RuntimeAlertRule.tenant_id == tenant_id).order_by(RuntimeAlertRule.name))).scalars().all())

    async def create_alert_rule(self, tenant_id: UUID, name: str, metric_name: str, operator: str, threshold: float, window_minutes: int, severity: str, actor: str) -> RuntimeAlertRule:
        """创建确定性告警规则并记录运维审计。"""
        if operator not in {">", ">=", "<", "<=", "=="}:
            raise ValueError("unsupported alert operator")
        if window_minutes < 1 or window_minutes > 10080:
            raise ValueError("window_minutes must be between 1 and 10080")
        if severity not in {"info", "warning", "critical"}:
            raise ValueError("unsupported alert severity")
        item = RuntimeAlertRule(tenant_id=tenant_id, name=name, metric_name=metric_name, operator=operator, threshold=threshold, window_minutes=window_minutes, severity=severity, enabled=True)
        self.db.add(item)
        await self.db.flush()
        await self.audit(tenant_id, actor, "alert_rule.create", "alert_rule", str(item.id), "success", {"metric_name": metric_name, "operator": operator, "threshold": threshold})
        return item

    async def snapshot(self, tenant_id: UUID, window_hours: int = 24) -> int:
        """把当前 Durable facts 聚合结果固化为时间序列样本，便于趋势查询与外部监控采集。"""
        overview = await self.metrics.overview(tenant_id, window_hours=window_hours)
        now = datetime.now(UTC).replace(tzinfo=None)
        values = {
            "runtime.delivery.success_percent": float(overview["slo"]["delivery_success_percent"]),
            "runtime.delivery.retry_count": float(overview["deliveries"]["retry_count"]),
            "runtime.delivery.dead_letter_count": float(overview["deliveries"]["dead_letter_count"]),
            "runtime.delivery.p95_latency_ms": float(overview["slo"]["p95_delivery_latency_ms"] or 0.0),
        }
        self.db.add_all([RuntimeMetricSample(tenant_id=tenant_id, metric_name=name, value=value, dimensions={}, recorded_at=now) for name, value in values.items()])
        return len(values)

    async def series(self, tenant_id: UUID, metric_name: str, window_minutes: int = 60) -> list[RuntimeMetricSample]:
        """查询当前租户指定指标的时间序列。"""
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=min(max(window_minutes, 1), 10080))
        return list((await self.db.execute(select(RuntimeMetricSample).where(RuntimeMetricSample.tenant_id == tenant_id, RuntimeMetricSample.metric_name == metric_name, RuntimeMetricSample.recorded_at >= since).order_by(RuntimeMetricSample.recorded_at))).scalars().all())

    async def audit(self, tenant_id: UUID, actor: str, action: str, resource_type: str, resource_id: str | None, outcome: str, details: dict[str, Any]) -> RuntimeOperationAudit:
        """写入不可变运维审计事实。"""
        item = RuntimeOperationAudit(tenant_id=tenant_id, actor=actor, action=action, resource_type=resource_type, resource_id=resource_id, outcome=outcome, details=details)
        self.db.add(item)
        return item

    async def audit_list(self, tenant_id: UUID, limit: int = 100) -> list[RuntimeOperationAudit]:
        """查询当前租户运维审计事实。"""
        return list((await self.db.execute(select(RuntimeOperationAudit).where(RuntimeOperationAudit.tenant_id == tenant_id).order_by(RuntimeOperationAudit.created_at.desc()).limit(min(max(limit, 1), 1000)))).scalars().all())

    async def prometheus(self, tenant_id: UUID) -> str:
        """输出 Prometheus 文本格式指标，指标来源为 Durable facts。"""
        overview = await self.metrics.overview(tenant_id)
        values = {
            "runtime_delivery_success_percent": overview["slo"]["delivery_success_percent"],
            "runtime_delivery_retry_count": overview["deliveries"]["retry_count"],
            "runtime_delivery_dead_letter_count": overview["deliveries"]["dead_letter_count"],
            "runtime_delivery_p95_latency_ms": overview["slo"]["p95_delivery_latency_ms"] or 0,
        }
        return "\n".join(f"{name}{{tenant_id=\"{tenant_id}\"}} {value}" for name, value in values.items()) + "\n"

    async def otlp(self, tenant_id: UUID) -> dict[str, Any]:
        """输出可供 OTLP HTTP 适配层消费的结构化指标数据。"""
        overview = await self.metrics.overview(tenant_id)
        timestamp = int(datetime.now(UTC).timestamp() * 1_000_000_000)
        values = [
            ("runtime.delivery.success_percent", overview["slo"]["delivery_success_percent"]),
            ("runtime.delivery.retry_count", overview["deliveries"]["retry_count"]),
            ("runtime.delivery.dead_letter_count", overview["deliveries"]["dead_letter_count"]),
            ("runtime.delivery.p95_latency_ms", overview["slo"]["p95_delivery_latency_ms"] or 0),
        ]
        return {"resourceMetrics": [{"resource": {"attributes": [{"key": "tenant.id", "value": {"stringValue": str(tenant_id)}}]}, "scopeMetrics": [{"scope": {"name": "enterprise-ai-agent-platform.runtime"}, "metrics": [{"name": name, "gauge": {"dataPoints": [{"asDouble": value, "timeUnixNano": str(timestamp)}]}} for name, value in values]}]}]}
