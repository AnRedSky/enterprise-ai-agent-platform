"""Runtime Operations 确定性告警评估。

职责：基于租户时间序列样本评估告警规则，并只记录真正发生的状态转换。
边界：不发送通知、不修改 Delivery/Integration Event 状态；通知层应消费返回的 firing/recovery transition。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.runtime_operations import RuntimeAlertRule, RuntimeMetricSample, RuntimeOperationAudit


OPERATORS: dict[str, Callable[[float, float], bool]] = {
    ">": lambda value, threshold: value > threshold,
    ">=": lambda value, threshold: value >= threshold,
    "<": lambda value, threshold: value < threshold,
    "<=": lambda value, threshold: value <= threshold,
    "==": lambda value, threshold: value == threshold,
}


class RuntimeAlertEvaluator:
    """按最新样本评估启用规则，并提供去重后的生命周期转换。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(self, tenant_id: UUID, *, actor: str = "system") -> list[dict[str, Any]]:
        """评估单租户告警规则，仅返回状态发生变化的 firing/recovery 事实。

        Args:
            tenant_id: 租户标识，所有规则、样本和历史状态均限定在该租户内。
            actor: 写入运维审计的执行主体。

        Returns:
            发生生命周期变化的告警事实列表；首次进入 normal 不产生通知转换。

        Raises:
            无：非法规则会被安全跳过，不影响其他规则评估。
        """
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
                "rule_id": rule.id,
                "rule_name": rule.name,
                "metric_name": rule.metric_name,
                "value": float(sample.value),
                "threshold": float(rule.threshold),
                "operator": rule.operator,
                "severity": rule.severity,
                "state": state,
                "transition": "firing" if state == "firing" else "recovery",
                "evaluated_at": now,
                "sample_id": sample.id,
            }
            transitions.append(transition)
            await self._audit_transition(tenant_id, actor, transition)
        return transitions

    async def _latest_state(self, tenant_id: UUID, rule_id: UUID) -> str | None:
        """读取当前租户指定规则最近一次生命周期状态。"""
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
        """持久化不可重复触发的告警生命周期转换事实。"""
        self.db.add(RuntimeOperationAudit(
            tenant_id=tenant_id,
            actor=actor,
            action="alert.transition",
            resource_type="alert_rule",
            resource_id=str(transition["rule_id"]),
            outcome=transition["state"],
            details={
                "transition": transition["transition"],
                "rule_name": transition["rule_name"],
                "metric_name": transition["metric_name"],
                "value": transition["value"],
                "threshold": transition["threshold"],
                "operator": transition["operator"],
                "severity": transition["severity"],
                "sample_id": str(transition["sample_id"]),
            },
        ))
