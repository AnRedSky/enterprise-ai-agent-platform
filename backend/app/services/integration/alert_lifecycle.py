"""Alert Rule 生命周期与通知编排。

职责：维护告警 firing/recovery 状态机，并把告警转换为可审计、可去重的通知投递事实。
边界：不执行外部网络请求；WebhookDeliveryWorker 是唯一实际网络投递入口。
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_event import IntegrationEventRecord
from app.models.runtime_operations import (
    RuntimeAlertInstance,
    RuntimeAlertRule,
    RuntimeMetricSample,
    RuntimeNotificationDelivery,
    RuntimeNotificationGroup,
    RuntimeNotificationPolicy,
    RuntimeOperationAudit,
)
from app.models.webhook_integration import WebhookDestination
from app.services.integration.notification_delivery import AlertNotificationDeliveryService
from app.services.integration.publisher import RuntimeIntegrationEventPublisher


class AlertLifecycleService:
    """Evaluate runtime alert rules and orchestrate notification delivery."""

    VALID_SEVERITIES = {"info", "warning", "critical"}

    def __init__(self, db: AsyncSession, *, actor: str = "alert-runtime") -> None:
        self.db = db
        self.actor = actor
        self.publisher = RuntimeIntegrationEventPublisher(db)
        self.delivery = AlertNotificationDeliveryService(db)

    async def evaluate_rule(
        self,
        rule: RuntimeAlertRule,
        sample: RuntimeMetricSample,
        *,
        now: datetime | None = None,
        dimensions: dict[str, Any] | None = None,
    ) -> RuntimeAlertInstance:
        now = now or datetime.now(UTC).replace(tzinfo=None)
        result = await self.db.execute(
            select(RuntimeAlertInstance).where(
                RuntimeAlertInstance.tenant_id == rule.tenant_id,
                RuntimeAlertInstance.rule_id == rule.id,
            )
        )
        instance = result.scalar_one_or_none()
        if instance is None:
            instance = RuntimeAlertInstance(
                id=uuid.uuid4(),
                tenant_id=rule.tenant_id,
                rule_id=rule.id,
                metric_name=rule.metric_name,
                routing_key=f"alert.{rule.name}",
            )
            self.db.add(instance)
            await self.db.flush()
        instance.last_value = sample.value
        transition = None
        firing = self._matches(rule.operator, sample.value, rule.threshold)
        if firing and instance.state != "firing":
            transition = "firing"
            instance.state = "firing"
            instance.fire_count += 1
            instance.first_fired_at = instance.first_fired_at or now
            instance.last_fired_at = now
            instance.recovered_at = None
        elif not firing and instance.state == "firing":
            transition = "recovery"
            instance.state = "recovered"
            instance.recovered_at = now
        instance.last_transition, instance.updated_at = transition, now
        if transition:
            await self._emit_transition(instance, rule, sample, transition, dimensions or {}, now)
        return instance

    async def _emit_transition(
        self,
        instance: RuntimeAlertInstance,
        rule: RuntimeAlertRule,
        sample: RuntimeMetricSample,
        transition: str,
        dimensions: dict[str, Any],
        now: datetime,
    ) -> None:
        """发布生命周期事件并应用 policy、cooldown、grouping 与 routing 规则。"""
        severity, level = self._escalate(rule.severity, instance.fire_count, rule)
        instance.severity, instance.escalation_level = severity, level
        # RuntimeMetricSample / alert instance timestamps are persisted as naive UTC.
        # IntegrationEvent's immutable contract requires an aware timestamp, so convert
        # the service's internal UTC value only at the integration-event boundary.
        occurred_at = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
        event = await self.publisher.publish(
            tenant_id=instance.tenant_id,
            event_type=f"alert.{transition}",
            source="alert-runtime",
            subject=f"alert:{instance.id}",
            idempotency_key=f"alert:{instance.id}:{transition}:{instance.fire_count}",
            payload={
                "alert_instance_id": str(instance.id),
                "rule_id": str(rule.id),
                "metric_name": rule.metric_name,
                "value": sample.value,
                "threshold": rule.threshold,
                "operator": rule.operator,
                "severity": severity,
                "routing_key": instance.routing_key,
                "transition": transition,
                "dimensions": dimensions,
                "escalation_level": level,
            },
            occurred_at=occurred_at,
        )
        policy = await self._select_policy(instance.tenant_id, severity, instance.routing_key)
        if policy is None:
            await self._audit(instance, "notification.route.no_policy", "failure", {"severity": severity}, now)
            await self._metric(instance.tenant_id, "notification.policy_miss", 1, {"severity": severity}, now)
            return
        if transition == "firing" and instance.next_notification_at and now < instance.next_notification_at:
            await self._audit(instance, "notification.suppressed", "success", {"reason": "cooldown"}, now)
            await self._metric(
                instance.tenant_id,
                "notification.suppressed",
                1,
                {"severity": severity, "reason": "cooldown"},
                now,
            )
            return
        instance.next_notification_at = now + timedelta(seconds=max(0, policy.cooldown_seconds))
        await self._route_notification(instance, event, transition, severity, policy, now)

    def _escalate(self, base_severity: str, fire_count: int, rule: RuntimeAlertRule) -> tuple[str, int]:
        """按 fire_count 应用有序 escalation 规则。"""
        severity = base_severity if base_severity in self.VALID_SEVERITIES else "warning"
        level = 0
        for item in sorted(rule.escalation or [], key=lambda value: int(value.get("after", 0))):
            if fire_count >= int(item.get("after", 0)):
                level, severity = int(item.get("level", level + 1)), str(item.get("severity", severity))
        return severity, level
