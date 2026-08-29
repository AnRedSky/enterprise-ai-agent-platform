"""Deterministic Runtime Operations alert evaluation.

The evaluator deliberately operates only on tenant-scoped durable metric samples and
alert rules. It does not send notifications or mutate Delivery state. A caller can
publish a returned transition as an Integration Event through the normal event path.
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
    """Evaluate enabled rules using the newest sample in each rule window."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(self, tenant_id: UUID, *, actor: str = "system") -> list[dict[str, Any]]:
        """Evaluate all enabled rules for one tenant and return transition facts.

        Rules with no sample in their window are ignored. The database is only used
        for reading rules/samples and writing an operational audit for each firing or
        recovery transition; no Delivery or Integration Event state is modified here.
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
            transition = {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "metric_name": rule.metric_name,
                "value": float(sample.value),
                "threshold": float(rule.threshold),
                "operator": rule.operator,
                "severity": rule.severity,
                "state": "firing" if firing else "normal",
                "evaluated_at": now,
                "sample_id": sample.id,
            }
            transitions.append(transition)
            await self._audit_transition(tenant_id, actor, transition)
        return transitions

    async def _audit_transition(self, tenant_id: UUID, actor: str, transition: dict[str, Any]) -> None:
        """Persist a compact, tenant-scoped operational evaluation fact."""
        self.db.add(RuntimeOperationAudit(
            tenant_id=tenant_id,
            actor=actor,
            action="alert.evaluate",
            resource_type="alert_rule",
            resource_id=str(transition["rule_id"]),
            outcome=transition["state"],
            details={
                "rule_name": transition["rule_name"],
                "metric_name": transition["metric_name"],
                "value": transition["value"],
                "threshold": transition["threshold"],
                "operator": transition["operator"],
                "severity": transition["severity"],
                "sample_id": str(transition["sample_id"]),
            },
        ))
