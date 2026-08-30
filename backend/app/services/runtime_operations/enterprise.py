"""Runtime 运维企业扩展服务。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.runtime_operations import RuntimeAlertRule, RuntimeMetricSample, RuntimeOperationAudit, RuntimeProviderRegistry
from app.models.webhook_integration import WebhookDestination
from app.services.runtime_operations.metrics_contract import RuntimeMetricContract
from app.services.runtime_operations.service import RuntimeOperationsService
from app.services.runtime_operations.sampling import RuntimeDimensionSampler


class RuntimeOperationsEnterpriseService:
    """提供 2.10-I 的注册、时间序列、导出、审计和配置生命周期能力。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.metrics = RuntimeOperationsService(db)
        self.dimension_sampler = RuntimeDimensionSampler(db)

    async def providers(self, tenant_id: UUID) -> list[RuntimeProviderRegistry]:
        return list((await self.db.execute(select(RuntimeProviderRegistry).where(RuntimeProviderRegistry.tenant_id == tenant_id).order_by(RuntimeProviderRegistry.name))).scalars().all())

    async def create_provider(self, tenant_id: UUID, name: str, provider_type: str, config: dict, actor: str) -> RuntimeProviderRegistry:
        forbidden = {"api_key", "apikey", "token", "password", "secret", "secret_value", "authorization", "credential", "credentials"}

        def contains_forbidden(value: Any) -> bool:
            if isinstance(value, dict):
                return any(str(key).lower() in forbidden or contains_forbidden(nested) for key, nested in value.items())
            if isinstance(value, list):
                return any(contains_forbidden(item) for item in value)
            return False

        if contains_forbidden(config):
            raise ValueError("provider config must not contain raw secrets")
        capabilities = config.get("capabilities", [])
        if not isinstance(capabilities, list) or len(capabilities) > 50 or any(not isinstance(item, str) or not item.strip() for item in capabilities):
            raise ValueError("provider capabilities must be a list of up to 50 non-empty strings")
        item = RuntimeProviderRegistry(tenant_id=tenant_id, name=name, provider_type=provider_type, config=config, enabled=True)
        self.db.add(item)
        await self.db.flush()
        await self.audit(tenant_id, actor, "provider.create", "provider", str(item.id), "success", {"name": name, "provider_type": provider_type, "capabilities": capabilities})
        return item

    async def set_provider_enabled(self, tenant_id: UUID, provider_id: UUID, enabled: bool, actor: str) -> RuntimeProviderRegistry:
        item = await self.db.scalar(select(RuntimeProviderRegistry).where(RuntimeProviderRegistry.tenant_id == tenant_id, RuntimeProviderRegistry.id == provider_id))
        if item is None:
            raise ValueError("provider not found")
        item.enabled = enabled
        await self.db.flush()
        await self.audit(tenant_id, actor, "provider.enable" if enabled else "provider.disable", "provider", str(provider_id), "success", {"enabled": enabled})
        return item

    async def destinations(self, tenant_id: UUID) -> list[WebhookDestination]:
        return list((await self.db.execute(select(WebhookDestination).where(WebhookDestination.tenant_id == tenant_id).order_by(WebhookDestination.name))).scalars().all())

    async def alerts_rules(self, tenant_id: UUID) -> list[RuntimeAlertRule]:
        return list((await self.db.execute(select(RuntimeAlertRule).where(RuntimeAlertRule.tenant_id == tenant_id).order_by(RuntimeAlertRule.name))).scalars().all())

    async def create_alert_rule(self, tenant_id: UUID, name: str, metric_name: str, operator: str, threshold: float, window_minutes: int, severity: str, actor: str) -> RuntimeAlertRule:
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

    async def set_alert_rule_enabled(self, tenant_id: UUID, rule_id: UUID, enabled: bool, actor: str) -> RuntimeAlertRule:
        item = await self.db.scalar(select(RuntimeAlertRule).where(RuntimeAlertRule.tenant_id == tenant_id, RuntimeAlertRule.id == rule_id))
        if item is None:
            raise ValueError("alert rule not found")
        item.enabled = enabled
        await self.db.flush()
        await self.audit(tenant_id, actor, "alert_rule.enable" if enabled else "alert_rule.disable", "alert_rule", str(rule_id), "success", {"enabled": enabled})
        return item

    async def snapshot(self, tenant_id: UUID, window_hours: int = 24) -> int:
        """生成租户级及三维 Runtime 指标快照。

        Args:
            tenant_id: 目标租户标识。
            window_hours: Durable facts 聚合窗口，限制由采样服务统一处理。

        Returns:
            本轮写入的 RuntimeMetricSample 数量。

        设计意图：全局摘要和 Provider/Destination/Event Type 维度都从同一组 Durable facts 派生，避免指标层形成第二套业务事实。
        """
        overview = await self.metrics.overview(tenant_id, window_hours=window_hours)
        now = datetime.now(UTC).replace(tzinfo=None)
        values = {
            "runtime.delivery.success_percent": float(overview["slo"]["delivery_success_percent"]),
            "runtime.delivery.retry_count": float(overview["deliveries"]["retry_count"]),
            "runtime.delivery.dead_letter_count": float(overview["deliveries"]["dead_letter_count"]),
            "runtime.delivery.p95_latency_ms": float(overview["slo"]["p95_delivery_latency_ms"] or 0.0),
        }
        self.db.add_all([RuntimeMetricSample(tenant_id=tenant_id, metric_name=name, value=value, dimensions={}, recorded_at=now) for name, value in values.items()])
        return len(values) + await self.dimension_sampler.sample(tenant_id, window_hours=window_hours)

    async def series(self, tenant_id: UUID, metric_name: str, window_minutes: int = 60, *, dimension_key: str | None = None, dimension_value: str | None = None) -> list[RuntimeMetricSample]:
        """按租户、指标和可选维度查询时间序列。

        Args:
            tenant_id: 目标租户标识。
            metric_name: 指标名称。
            window_minutes: 查询时间窗口，最大 10080 分钟。
            dimension_key: 可选维度键，仅允许 provider、destination_id、event_type。
            dimension_value: 与维度键匹配的字符串值。

        Returns:
            按记录时间升序排列的指标样本。
        """
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=min(max(window_minutes, 1), 10080))
        stmt = select(RuntimeMetricSample).where(RuntimeMetricSample.tenant_id == tenant_id, RuntimeMetricSample.metric_name == metric_name, RuntimeMetricSample.recorded_at >= since)
        if dimension_key is not None:
            if dimension_key not in {"provider", "destination_id", "event_type"}:
                raise ValueError("unsupported metric dimension")
            if dimension_value is None:
                raise ValueError("dimension_value is required when dimension_key is provided")
            stmt = stmt.where(RuntimeMetricSample.dimensions[dimension_key].as_string() == dimension_value)
        return list((await self.db.execute(stmt.order_by(RuntimeMetricSample.recorded_at))).scalars().all())

    async def audit(self, tenant_id: UUID, actor: str, action: str, resource_type: str, resource_id: str | None, outcome: str, details: dict[str, Any]) -> RuntimeOperationAudit:
        item = RuntimeOperationAudit(tenant_id=tenant_id, actor=actor, action=action, resource_type=resource_type, resource_id=resource_id, outcome=outcome, details=details)
        self.db.add(item)
        return item

    async def audit_list(self, tenant_id: UUID, limit: int = 100) -> list[RuntimeOperationAudit]:
        """复用 Runtime 基础服务的 tenant-scoped Audit 查询，避免形成第二套查询规则。"""
        return await self.metrics.audit_list(tenant_id, limit=limit)

    async def prometheus(self, tenant_id: UUID) -> str:
        """按规范指标名和唯一 tenant_id 标签导出 Prometheus 数据。"""
        overview = await self.metrics.overview(tenant_id)
        values = {
            "runtime.delivery.success_percent": overview["slo"]["delivery_success_percent"],
            "runtime.delivery.retry_count": overview["deliveries"]["retry_count"],
            "runtime.delivery.dead_letter_count": overview["deliveries"]["dead_letter_count"],
            "runtime.delivery.p95_latency_ms": overview["slo"]["p95_delivery_latency_ms"],
        }
        return RuntimeMetricContract.prometheus(tenant_id, values)

    async def otlp(self, tenant_id: UUID) -> dict[str, Any]:
        """按统一 Resource 属性生成 OTLP HTTP 指标结构。"""
        overview = await self.metrics.overview(tenant_id)
        values = {
            "runtime.delivery.success_percent": overview["slo"]["delivery_success_percent"],
            "runtime.delivery.retry_count": overview["deliveries"]["retry_count"],
            "runtime.delivery.dead_letter_count": overview["deliveries"]["dead_letter_count"],
            "runtime.delivery.p95_latency_ms": overview["slo"]["p95_delivery_latency_ms"],
        }
        return RuntimeMetricContract.otlp(tenant_id, values)
