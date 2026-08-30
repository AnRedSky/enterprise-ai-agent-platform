"""Alert Rule 生命周期与通知编排。"""
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
    """维护告警状态机，并完成 Alert -> Notification 的持久化编排。"""

    VALID_OPERATORS = frozenset({">", ">=", "<", "<=", "==", "!="})
    VALID_SEVERITIES = frozenset({"info", "warning", "critical", "fatal"})
    NOTIFICATION_STATUSES = frozenset({"planned", "delivered", "retrying", "failed", "dead_letter"})
    TERMINAL_NOTIFICATION_STATUSES = frozenset({"delivered", "dead_letter"})

    def __init__(self, db: AsyncSession, *, actor: str = "runtime-alert-engine", consumer_group: str = "default"):
        consumer_group = consumer_group.strip()
        if not consumer_group or len(consumer_group) > 128:
            raise ValueError("consumer_group 必须为 1..128 个字符")
        self.db, self.actor, self.consumer_group = db, actor, consumer_group
        self.publisher = RuntimeIntegrationEventPublisher(db)
        self.delivery = AlertNotificationDeliveryService(db)

    @classmethod
    def matches(cls, value: float, operator: str, threshold: float) -> bool:
        if operator not in cls.VALID_OPERATORS:
            raise ValueError(f"unsupported alert operator: {operator}")
        return {">": value > threshold, ">=": value >= threshold, "<": value < threshold,
                "<=": value <= threshold, "==": value == threshold, "!=": value != threshold}[operator]

    @staticmethod
    def fingerprint(rule: RuntimeAlertRule, dimensions: dict[str, Any] | None = None) -> str:
        canonical = f"{rule.tenant_id}:{rule.id}:{sorted((dimensions or {}).items())}"
        return hashlib.sha256(canonical.encode()).hexdigest()

    async def evaluate_rule(self, rule: RuntimeAlertRule, sample: RuntimeMetricSample, *, now: datetime | None = None, dimensions: dict[str, Any] | None = None) -> RuntimeAlertInstance | None:
        now = now or datetime.now(UTC).replace(tzinfo=None)
        if rule.tenant_id != sample.tenant_id or rule.metric_name != sample.metric_name or not rule.enabled:
            return None
        matched = self.matches(sample.value, rule.operator, rule.threshold)
        fingerprint = self.fingerprint(rule, dimensions or sample.dimensions)
        instance = await self.db.scalar(select(RuntimeAlertInstance).where(
            RuntimeAlertInstance.tenant_id == rule.tenant_id,
            RuntimeAlertInstance.fingerprint == fingerprint,
        ).with_for_update())
        if instance is None:
            if not matched:
                return None
            instance = RuntimeAlertInstance(
                id=uuid.uuid4(), tenant_id=rule.tenant_id, rule_id=rule.id, fingerprint=fingerprint,
                state="firing", severity=rule.severity, routing_key="",
                fire_count=1, first_fired_at=now, last_fired_at=now, next_notification_at=None,
                last_value=sample.value, last_transition="firing",
            )
            self.db.add(instance)
            await self.db.flush()
            await self._emit_transition(instance, rule, sample, "firing", dimensions or sample.dimensions, now)
            return instance
        if matched:
            instance.state = "firing"
            instance.severity = rule.severity
            instance.fire_count += 1
            instance.last_fired_at = now
            instance.last_value = sample.value
            instance.last_transition = "firing"
            await self._emit_transition(instance, rule, sample, "firing", dimensions or sample.dimensions, now)
        elif instance.state == "firing":
            instance.state = "resolved"
            instance.recovered_at = now
            instance.last_value = sample.value
            instance.last_transition = "recovery"
            await self._emit_transition(instance, rule, sample, "recovery", dimensions or sample.dimensions, now)
        return instance

    async def _emit_transition(self, instance: RuntimeAlertInstance, rule: RuntimeAlertRule, sample: RuntimeMetricSample, transition: str, dimensions: dict[str, Any], now: datetime) -> None:
        severity, level = self._escalate(instance.severity, instance.fire_count, rule)
        instance.severity = severity
        instance.escalation_level = level
        event = await self.publisher.publish(
            tenant_id=instance.tenant_id, event_type=f"alert.{transition}", source="alert_lifecycle",
            subject=str(instance.id), idempotency_key=f"alert:{instance.id}:{transition}:{instance.fire_count}",
            payload={
                "alert_instance_id": str(instance.id), "rule_id": str(rule.id), "metric_name": sample.metric_name,
                "value": sample.value, "threshold": rule.threshold, "severity": severity,
                "routing_key": instance.routing_key, "transition": transition, "dimensions": dimensions,
                "escalation_level": level,
            },
            occurred_at=now,
        )
        policy = await self._select_policy(instance.tenant_id, severity, instance.routing_key or None)
        if policy is None:
            await self._audit(instance, "notification.route.no_policy", "failure", {"severity": severity}, now)
            await self._metric(instance.tenant_id, "notification.policy_miss", 1, {"severity": severity}, now)
            return
        if not instance.routing_key and policy.routing_key:
            instance.routing_key = policy.routing_key
        if transition == "firing" and instance.next_notification_at and now < instance.next_notification_at:
            await self._audit(instance, "notification.suppressed", "success", {"reason": "cooldown"}, now)
            await self._metric(instance.tenant_id, "notification.suppressed", 1, {"severity": severity, "reason": "cooldown"}, now)
            return
        instance.next_notification_at = now + timedelta(seconds=max(0, policy.cooldown_seconds))
        await self._route_notification(instance, event, transition, severity, policy, now)

    def _escalate(self, base_severity: str, fire_count: int, rule: RuntimeAlertRule) -> tuple[str, int]:
        severity = base_severity if base_severity in self.VALID_SEVERITIES else "warning"
        level = 0
        for item in sorted(rule.escalation or [], key=lambda value: int(value.get("after", 0))):
            if fire_count >= int(item.get("after", 0)):
                level, severity = int(item.get("level", level + 1)), str(item.get("severity", severity))
        return severity, level

    async def _select_policy(self, tenant_id: uuid.UUID, severity: str, routing_key: str | None) -> RuntimeNotificationPolicy | None:
        """在 tenant scope 内优先选择精确 routing key，否则允许无 routing key 的规则走 severity 路由。"""
        policies = list((await self.db.execute(select(RuntimeNotificationPolicy).where(
            RuntimeNotificationPolicy.tenant_id == tenant_id,
            RuntimeNotificationPolicy.enabled.is_(True),
        ).order_by(RuntimeNotificationPolicy.id))).scalars().all())
        exact = next((p for p in policies if p.severity in (None, severity) and routing_key and p.routing_key == routing_key), None)
        if exact is not None:
            return exact
        return next((p for p in policies if p.severity in (None, severity) and (p.routing_key is None or not routing_key)), None)

    async def _route_notification(self, instance: RuntimeAlertInstance, event: IntegrationEventRecord, transition: str, severity: str, policy: RuntimeNotificationPolicy, now: datetime, exclude_providers: list[str] | None = None) -> list[RuntimeNotificationDelivery]:
        group_key = f"{instance.tenant_id}:{policy.name}:{severity}:{instance.routing_key}"
        group = await self.db.scalar(select(RuntimeNotificationGroup).where(
            RuntimeNotificationGroup.tenant_id == instance.tenant_id,
            RuntimeNotificationGroup.group_key == group_key,
        ))
        if group is None or group.closed_at is not None or now - group.last_event_at > timedelta(seconds=policy.group_window_seconds):
            group = RuntimeNotificationGroup(tenant_id=instance.tenant_id, group_key=group_key, severity=severity, routing_key=instance.routing_key, first_event_at=now, last_event_at=now)
            self.db.add(group)
        else:
            group.last_event_at, group.event_count = now, group.event_count + 1
        await self.db.flush()
        deliveries = await self.delivery.dispatch_event(
            event,
            destination_ids=[uuid.UUID(str(v)) for v in policy.destination_ids],
            provider_order=policy.provider_order,
            fallback=True,
            exclude_providers=exclude_providers,
            consumer_group=self.consumer_group,
        )
        records: list[RuntimeNotificationDelivery] = []
        for delivery in deliveries:
            destination = await self.db.get(WebhookDestination, delivery.destination_id)
            provider = destination.provider if destination else None
            dedup_key = self.notification_dedup_key(instance, transition, group.id, delivery.destination_id, provider)
            statement = pg_insert(RuntimeNotificationDelivery).values(
                id=uuid.uuid4(), tenant_id=instance.tenant_id, alert_instance_id=instance.id, group_id=group.id,
                integration_event_id=event.id, webhook_delivery_id=delivery.id, transition=transition, provider=provider,
                dedup_key=dedup_key, status="planned", attempt_count=0,
            ).on_conflict_do_nothing(constraint="uq_runtime_notification_delivery_dedup")
            await self.db.execute(statement)
            record = await self.db.scalar(select(RuntimeNotificationDelivery).where(
                RuntimeNotificationDelivery.tenant_id == instance.tenant_id,
                RuntimeNotificationDelivery.dedup_key == dedup_key,
            ))
            if record is None:
                continue
            records.append(record)
            await self._audit(instance, "notification.route", "success", {
                "transition": transition, "delivery_id": str(delivery.id), "provider": provider,
                "group_id": str(group.id), "severity": severity, "dedup_key": dedup_key,
            }, now)
            await self._metric(instance.tenant_id, "notification.routed", 1, {
                "provider": provider or "unknown", "severity": severity, "transition": transition,
            }, now)
        if not deliveries:
            await self._audit(instance, "notification.route.empty", "failure", {"policy_id": str(policy.id)}, now)
            await self._metric(instance.tenant_id, "notification.route_empty", 1, {"severity": severity}, now)
        await self.db.flush()
        return records

    async def record_delivery_outcome(self, webhook_delivery_id: uuid.UUID, *, status: str, error_code: str | None = None, error_message: str | None = None, now: datetime | None = None) -> RuntimeNotificationDelivery | None:
        if status not in self.NOTIFICATION_STATUSES:
            raise ValueError(f"unsupported notification status: {status}")
        now = now or datetime.now(UTC).replace(tzinfo=None)
        record = await self.db.scalar(select(RuntimeNotificationDelivery).where(
            RuntimeNotificationDelivery.webhook_delivery_id == webhook_delivery_id
        ).order_by(RuntimeNotificationDelivery.created_at.desc()))
        if record is None:
            return None
        if record.status in self.TERMINAL_NOTIFICATION_STATUSES:
            return record
        record.status = status
        record.attempt_count += 1
        record.last_error_code, record.last_error_message, record.updated_at = error_code, error_message, now
        outcome = "failure" if status in {"failed", "dead_letter"} else "success"
        await self._audit_for_delivery(record, f"notification.delivery.{status}", outcome, now)
        await self._metric(record.tenant_id, f"notification.delivery.{status}", 1, {"provider": record.provider or "unknown"}, now)
        if status == "dead_letter" and record.integration_event_id is not None and record.provider:
            event = await self.db.get(IntegrationEventRecord, record.integration_event_id)
            instance = await self.db.get(RuntimeAlertInstance, record.alert_instance_id)
            if event is not None and instance is not None:
                policy = await self._select_policy(record.tenant_id, instance.severity, instance.routing_key or None)
                if policy is not None:
                    fallback_records = await self._route_notification(instance, event, record.transition, instance.severity, policy, now, exclude_providers=[record.provider])
                    if fallback_records:
                        await self._audit(instance, "notification.fallback.routed", "success", {"from_provider": record.provider, "to_provider": fallback_records[0].provider}, now)
                        await self._metric(record.tenant_id, "notification.fallback.routed", 1, {"from_provider": record.provider, "to_provider": fallback_records[0].provider or "unknown"}, now)
                    else:
                        await self._audit(instance, "notification.fallback.exhausted", "failure", {"provider": record.provider}, now)
                        await self._metric(record.tenant_id, "notification.dlq", 1, {"provider": record.provider, "transition": record.transition}, now)
        await self.db.flush()
        return record

    @staticmethod
    def notification_dedup_key(instance: RuntimeAlertInstance, transition: str, group_id: uuid.UUID, destination_id: uuid.UUID, provider: str | None) -> str:
        return hashlib.sha256(f"{instance.tenant_id}:{instance.id}:{transition}:{group_id}:{destination_id}:{provider}".encode()).hexdigest()

    async def _audit(self, instance: RuntimeAlertInstance, action: str, outcome: str, details: dict[str, Any], now: datetime) -> None:
        self.db.add(RuntimeOperationAudit(
            id=uuid.uuid4(), tenant_id=instance.tenant_id, action=action, outcome=outcome,
            resource_type="alert_instance", resource_id=str(instance.id), actor=self.actor,
            details=details, created_at=now,
        ))
        await self.db.flush()

    async def _audit_for_delivery(self, record: RuntimeNotificationDelivery, action: str, outcome: str, now: datetime) -> None:
        instance = await self.db.get(RuntimeAlertInstance, record.alert_instance_id)
        if instance is not None:
            await self._audit(instance, action, outcome, {
                "delivery_id": str(record.webhook_delivery_id), "provider": record.provider,
                "error_code": record.last_error_code,
            }, now)

    async def _metric(self, tenant_id: uuid.UUID, metric_name: str, value: float, dimensions: dict[str, Any], now: datetime) -> None:
        self.db.add(RuntimeMetricSample(
            tenant_id=tenant_id, metric_name=metric_name, value=value,
            dimensions=dimensions, recorded_at=now,
        ))
        await self.db.flush()
