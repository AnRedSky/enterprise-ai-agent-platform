"""Runtime Operations 确定性告警评估。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.runtime_operations import RuntimeAlertRule, RuntimeMetricSample, RuntimeOperationAudit
from app.services.integration.publisher import RuntimeIntegrationEventPublisher

OPERATORS: dict[str, Callable[[float, float], bool]] = {
    ">": lambda value, threshold: value > threshold,
    ">=": lambda value, threshold: value >= threshold,
    "<": lambda value, threshold: value < threshold,
    "<=": lambda value, threshold: value <= threshold,
    "==": lambda value, threshold: value == threshold,
}


class RuntimeAlertEvaluator:
    """按最新样本评估启用规则，并持久化去重后的告警生命周期转换。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_publisher = RuntimeIntegrationEventPublisher(db)

    async def evaluate(self, tenant_id: UUID, *, actor: str = "system") -> list[dict[str, Any]]:
        """评估单租户告警规则，并把 firing/recovery 转换写入 Durable Integration Event。"""
        rules = list((await self.db.execute(
            select(RuntimeAlertRule)
            .where(RuntimeAlertRule.tenant_id == tenant_id, RuntimeAlertRule.enabled.is_(True))
            .order_by(RuntimeAlertRule.id)
        )).scalars().all())
        now = datetime.now(UTC).replace(tzinfo=None)
        transitions: list[dict[str, Any]] = []
        for rule in rules:
            if rule.operator not in OPERATORS:
                continue
            since = now - timedelta(minutes=max(1, min(rule.window_minutes, 10080)))
            sample = await self.db.scalar(
                select(RuntimeMetricSample)
                .where(
                    RuntimeMetricSample.tenant_id == tenant_id,
                    RuntimeMetricSample.metric_name == rule.metric_name,
                    RuntimeMetricSample.recorded_at >= since,
                )
                .order_by(RuntimeMetricSample.recorded_at.desc(), RuntimeMetricSample.id.desc())
                .limit(1)
            )
            if sample is None:
                continue
            firing = OPERATORS[rule.operator](float(sample.value), float(rule.threshold))
            state = "firing" if firing else "normal"
            previous = await self._latest_state(tenant_id, rule.id)
            if previous == state or (previous is None and state == "normal"):
                continue
            transition = {
                "rule_id": rule.id, "rule_name": rule.name, "metric_name": rule.metric_name,
                "value": float(sample.value), "threshold": float(rule.threshold),
                "operator": rule.operator, "severity": rule.severity, "state": state,
                "transition": "firing" if state == "firing" else "recovery",
                "evaluated_at": now, "sample_id": sample.id,
            }
            transitions.append(transition)
            await self._audit_transition(tenant_id, actor, transition)
            await self._publish_transition(tenant_id, transition)
        return transitions

    async def _latest_state(self, tenant_id: UUID, rule_id: UUID) -> str | None:
        audit = await self.db.scalar(
            select(RuntimeOperationAudit)
            .where(
                RuntimeOperationAudit.tenant_id == tenant_id,
                RuntimeOperationAudit.action == "alert.transition",
                RuntimeOperationAudit.resource_id == str(rule_id),
            )
            .order_by(RuntimeOperationAudit.created_at.desc(), RuntimeOperationAudit.id.desc())
            .limit(1)
        )
        return audit.outcome if audit is not None else None

    async def _audit_transition(self, tenant_id: UUID, actor: str, transition: dict[str, Any]) -> None:
        self.db.add(RuntimeOperationAudit(
            tenant_id=tenant_id, actor=actor, action="alert.transition",
            resource_type="alert_rule", resource_id=str(transition["rule_id"]),
            outcome=transition["state"], details={
                "transition": transition["transition"], "rule_name": transition["rule_name"],
                "metric_name": transition["metric_name"], "value": transition["value"],
                "threshold": transition["threshold"], "operator": transition["operator"],
                "severity": transition["severity"], "sample_id": str(transition["sample_id"]),
            },
        ))

    async def _publish_transition(self, tenant_id: UUID, transition: dict[str, Any]) -> None:
        """把告警转换作为通知层唯一事实入口写入 Durable Integration Event。"""
        rule_id = transition["rule_id"]
        state = transition["state"]
        await self.event_publisher.publish(
            tenant_id=tenant_id,
            event_type=f"runtime.alert.{transition['transition']}",
            source="runtime-operations",
            subject=f"alert-rule:{rule_id}",
            idempotency_key=f"alert:{rule_id}:{state}:{transition['sample_id']}",
            payload={
                "rule_id": str(rule_id), "rule_name": transition["rule_name"],
                "metric_name": transition["metric_name"], "value": transition["value"],
                "threshold": transition["threshold"], "operator": transition["operator"],
                "severity": transition["severity"], "state": state,
                "sample_id": str(transition["sample_id"]),
            },
            metadata={"actor": "runtime-alert-evaluator"},
        )
