"""Alert Rule lifecycle -> notification orchestration.

This service owns deterministic alert state transitions. It writes the lifecycle fact,
creates a durable Integration Event for firing/recovery, applies notification policy,
and materializes delivery facts. Network I/O remains in WebhookDeliveryWorker.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
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
from app.services.integration.notification_delivery import AlertNotificationDeliveryService
from app.services.integration.publisher import RuntimeIntegrationEventPublisher


class AlertLifecycleService:
    """Evaluate one metric sample and drive the durable alert lifecycle."""

    VALID_OPERATORS = frozenset({">", ">=", "<", "<=", "==", "!="})
    VALID_SEVERITIES = frozenset({"info", "warning", "critical", "fatal"})

    def __init__(self, db: AsyncSession, *, actor: str = "runtime-alert-engine"):
        self.db = db
        self.actor = actor
        self.publisher = RuntimeIntegrationEventPublisher(db)
        self.delivery = AlertNotificationDeliveryService(db)

    @classmethod
    def matches(cls, value: float, operator: str, threshold: float) -> bool:
        if operator not in cls.VALID_OPERATORS:
            raise ValueError(f"unsupported alert operator: {operator}")
        return {
            ">": value > threshold, ">=": value >= threshold,
            "<": value < threshold, "<=": value <= threshold,
            "==": value == threshold, "!=": value != threshold,
        }[operator]

    @staticmethod
    def fingerprint(rule: RuntimeAlertRule, dimensions: dict[str, Any] | None = None) -> str:
        material = f"{rule.id}|{sorted((dimensions or {}).items())}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    async def evaluate_rule(
        self,
        rule: RuntimeAlertRule,
        sample: RuntimeMetricSample,
        *,
        dimensions: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> RuntimeAlertInstance:
        """Apply a sample to an alert instance and emit only real transitions."""
        if rule.tenant_id != sample.tenant_id or rule.metric_name != sample.metric_name:
            raise ValueError("alert rule and metric sample tenant/metric mismatch")
        if not rule.enabled:
            raise ValueError("cannot evaluate a disabled alert rule")
        now = now or sample.recorded_at
        firing = self.matches(sample.value, rule.operator, rule.threshold)
        fingerprint = self.fingerprint(rule, dimensions)
        instance = await self.db.scalar(select(RuntimeAlertInstance).where(
            RuntimeAlertInstance.tenant_id == rule.tenant_id,
            RuntimeAlertInstance.rule_id == rule.id,
            RuntimeAlertInstance.fingerprint == fingerprint,
        ))
        if instance is None:
            instance = RuntimeAlertInstance(
                tenant_id=rule.tenant_id, rule_id=rule.id, fingerprint=fingerprint,
                state="inactive", severity=rule.severity,
                routing_key=f"alert.{rule.name}",
            )
            self.db.add(instance)
            await self.db.flush()

        instance.last_value = sample.value
        transition = None
        if firing and instance.state != "firing":
            transition = "firing"
            instance.state = "firing"
            instance.severity = rule.severity
            instance.fire_count += 1
            instance.first_fired_at = instance.first_fired_at or now
            instance.last_fired_at = now
            instance.recovered_at = None
        elif not firing and instance.state == "firing":
            transition = "recovery"
            instance.state = "recovered"
            instance.recovered_at = now
        instance.last_transition = transition
        instance.updated_at = now

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
        severity, level = self._escalate(rule.severity, instance.fire_count, rule)
        instance.severity = severity
        instance.escalation_level = level
        event_type = f"alert.{transition}"
        event = await self.publisher.publish(
            tenant_id=instance.tenant_id,
            event_type=event_type,
            source="alert-runtime",
            subject=f"alert:{instance.id}",
            idempotency_key=f"alert:{instance.id}:{transition}:{instance.fire_count}",
            payload={
                "alert_instance_id": str(instance.id), "rule_id": str(rule.id),
                "metric_name": rule.metric_name, "value": sample.value,
                "threshold": rule.threshold, "operator": rule.operator,
                "severity": severity, "routing_key": instance.routing_key,
                "transition": transition, "dimensions": dimensions,
                "escalation_level": level,
            },
            occurred_at=now,
        )
        should_notify = transition == "recovery" or await self._notification_allowed(instance, severity, now)
        if should_notify:
            await self._route_notification(instance, event, transition, severity, now)
        else:
            await self._audit(instance, "notification.suppressed", "success", {"reason": "cooldown"}, now)

    def _escalate(self, base_severity: str, fire_count: int, rule: RuntimeAlertRule) -> tuple[str, int]:
        if base_severity not in self.VALID_SEVERITIES:
            base_severity = "warning"
        level = 0
        severity = base_severity
        # Optional rule extension without changing the stable rule schema: callers may
        # attach an ``escalation`` attribute in orchestration code.
        escalation = getattr(rule, "escalation", None) or []
        for item in sorted(escalation, key=lambda value: int(value.get("after", 0))):
            if fire_count >= int(item.get("after", 0)):
                level = int(item.get("level", level + 1))
                severity = str(item.get("severity", severity))
        return severity, level

    async def _notification_allowed(self, instance: RuntimeAlertInstance, severity: str, now: datetime) -> bool:
        if instance.next_notification_at and now < instance.next_notification_at:
            return False
        policy = await self._select_policy(instance.tenant_id, severity, instance.routing_key)
        if policy is None:
            return False
        instance.next_notification_at = now + timedelta(seconds=max(0, policy.cooldown_seconds))
        return True

    async def _select_policy(self, tenant_id: uuid.UUID, severity: str, routing_key: str) -> RuntimeNotificationPolicy | None:
        policies = list((await self.db.execute(select(RuntimeNotificationPolicy).where(
            RuntimeNotificationPolicy.tenant_id == tenant_id,
            RuntimeNotificationPolicy.enabled.is_(True),
        ).order_by(RuntimeNotificationPolicy.id))).scalars().all())
        for policy in policies:
            if policy.severity not in (None, severity):
                continue
            if policy.routing_key not in (None, routing_key):
                continue
            return policy
        return None

    async def _route_notification(
        self, instance: RuntimeAlertInstance, event: IntegrationEventRecord,
        transition: str, severity: str, now: datetime,
    ) -> None:
        policy = await self._select_policy(instance.tenant_id, severity, instance.routing_key)
        if policy is None:
            await self._audit(instance, "notification.route.no_policy", "failure", {"severity": severity}, now)
            return
        group_key = f"{instance.tenant_id}:{policy.name}:{severity}:{instance.routing_key}"
        group = await self.db.scalar(select(RuntimeNotificationGroup).where(
            RuntimeNotificationGroup.tenant_id == instance.tenant_id,
            RuntimeNotificationGroup.group_key == group_key,
        ))
        if group is None or group.closed_at is not None or now - group.last_event_at > timedelta(seconds=policy.group_window_seconds):
            group = RuntimeNotificationGroup(
                tenant_id=instance.tenant_id, group_key=group_key, severity=severity,
                routing_key=instance.routing_key, first_event_at=now, last_event_at=now,
            )
            self.db.add(group)
        else:
            group.last_event_at = now
            group.event_count += 1
        await self.db.flush()

        destinations = [uuid.UUID(str(value)) for value in policy.destination_ids]
        deliveries = await self.delivery.dispatch_event(
            event, destination_ids=destinations, provider_order=policy.provider_order,
            fallback=True,
        )
        for delivery in deliveries:
            provider = None
            destination = await self.db.get(__import__("app.models.webhook_integration", fromlist=["WebhookDestination"]).WebhookDestination, delivery.destination_id)
            if destination is not None:
                provider = destination.provider
            dedup_key = f"{instance.id}:{transition}:{group.id}:{delivery.destination_id}"
            record = RuntimeNotificationDelivery(
                tenant_id=instance.tenant_id, alert_instance_id=instance.id, group_id=group.id,
                integration_event_id=event.id, webhook_delivery_id=delivery.id,
                transition=transition, provider=provider, dedup_key=dedup_key, status="planned",
            )
            self.db.add(record)
            await self._audit(instance, "notification.route", "success", {
                "transition": transition, "delivery_id": str(delivery.id),
                "provider": provider, "group_id": str(group.id), "severity": severity,
            }, now)
        if not deliveries:
            await self._audit(instance, "notification.route.empty", "failure", {"policy_id": str(policy.id)}, now)
        await self.db.flush()

    async def _audit(self, instance: RuntimeAlertInstance, action: str, outcome: str, details: dict[str, Any], now: datetime) -> None:
        self.db.add(RuntimeOperationAudit(
            tenant_id=instance.tenant_id, actor=self.actor, action=action,
            resource_type="alert", resource_id=str(instance.id), outcome=outcome,
            details=details, created_at=now,
        ))


__all__ = ["AlertLifecycleService"]
