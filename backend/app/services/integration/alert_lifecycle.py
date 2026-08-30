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
    """维护告警状态机，并完成 Alert -> Notification 的持久化编排。"""

    VALID_OPERATORS = frozenset({">", ">=", "<", "<=", "==", "!="})
    VALID_SEVERITIES = frozenset({"info", "warning", "critical", "fatal"})
    NOTIFICATION_STATUSES = frozenset({"planned", "delivered", "retrying", "failed", "dead_letter"})
    TERMINAL_NOTIFICATION_STATUSES = frozenset({"delivered", "dead_letter"})

    def __init__(self, db: AsyncSession, *, actor: str = "runtime-alert-engine"):
        self.db, self.actor = db, actor
        self.publisher = RuntimeIntegrationEventPublisher(db)
        self.delivery = AlertNotificationDeliveryService(db)

    @classmethod
    def matches(cls, value: float, operator: str, threshold: float) -> bool:
        """判断指标值是否命中告警规则。"""
        if operator not in cls.VALID_OPERATORS:
            raise ValueError(f"unsupported alert operator: {operator}")
        return {
            ">": value > threshold,
            ">=": value >= threshold,
            "<": value < threshold,
            "<=": value <= threshold,
            "==": value == threshold,
            "!=": value != threshold,
        }[operator]

    @staticmethod
    def fingerprint(rule: RuntimeAlertRule, dimensions: dict[str, Any] | None = None) -> str:
        """根据规则与维度生成稳定告警实例指纹，避免跨租户状态串联。"""
        return hashlib.sha256(f"{rule.id}|{sorted((dimensions or {}).items())}".encode()).hexdigest()

    @staticmethod
    def notification_dedup_key(instance: RuntimeAlertInstance, transition: str, group_id: uuid.UUID, destination_id: uuid.UUID, provider: str | None) -> str:
        """生成一次告警生命周期投递的稳定幂等键。"""
        raw = ":".join([str(instance.tenant_id), str(instance.id), str(instance.fire_count), transition, str(group_id), str(destination_id), provider or "unknown"])
        return hashlib.sha256(raw.encode()).hexdigest()

    async def evaluate_rule(self, rule: RuntimeAlertRule, sample: RuntimeMetricSample, *, dimensions: dict[str, Any] | None = None, now: datetime | None = None) -> RuntimeAlertInstance:
        """评估一次指标并推进 firing/recovery 状态机。"""
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
                tenant_id=rule.tenant_id,
                rule_id=rule.id,
                fingerprint=fingerprint,
                state="inactive",
                severity=rule.severity,
                routing_key=f"alert.{rule.name}",
            )
            self.db.add(instance)
            await self.db.flush()
        instance.last_value = sample.value
        transition = None
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

    async def _emit_transition(self, instance: RuntimeAlertInstance, rule: RuntimeAlertRule, sample: RuntimeMetricSample, transition: str, dimensions: dict[str, Any], now: datetime) -> None:
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
                "alert_instance_id": str(instance.id), "rule_id": str(rule.id), "metric_name": rule.metric_name,
                "value": sample.value, "threshold": rule.threshold, "operator": rule.operator, "severity": severity,
                "routing_key": instance.routing_key, "transition": transition, "dimensions": dimensions,
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
            await self._metric(instance.tenant_id, "notification.suppressed", 1, {"severity": severity, "reason": "cooldown"}, now)
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

    async def _select_policy(self, tenant_id: uuid.UUID, severity: str, routing_key: str) -> RuntimeNotificationPolicy | None:
        """在 tenant scope 内选择最具体的启用通知策略。"""
        policies = list((await self.db.execute(select(RuntimeNotificationPolicy).where(
            RuntimeNotificationPolicy.tenant_id == tenant_id,
            RuntimeNotificationPolicy.enabled.is_(True),
        ).order_by(RuntimeNotificationPolicy.id))).scalars().all())
        return next((p for p in policies if p.severity in (None, severity) and p.routing_key in (None, routing_key)), None)

    async def _route_notification(self, instance: RuntimeAlertInstance, event: IntegrationEventRecord, transition: str, severity: str, policy: RuntimeNotificationPolicy, now: datetime, exclude_providers: list[str] | None = None) -> list[RuntimeNotificationDelivery]:
        """创建分组与通知 Delivery Fact；并发重复执行通过数据库幂等键收敛。"""
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
        deliveries = await self.delivery.dispatch_event(event, destination_ids=[uuid.UUID(str(v)) for v in policy.destination_ids], provider_order=policy.provider_order, fallback=True, exclude_providers=exclude_providers)
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
        """把 Worker 投递结果写回 Notification，并在终态死信时进入下一 Provider tier。"""
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
                policy = await self._select_policy(record.tenant_id, instance.severity, instance.routing_key)
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

    async def _audit_for_delivery(self, record: RuntimeNotificationDelivery, action: str, outcome: str, now: datetime) -> None:
        self.db.add(RuntimeOperationAudit(
            tenant_id=record.tenant_id, actor=self.actor, action=action, resource_type="notification_delivery",
            resource_id=str(record.id), outcome=outcome, details={
                "webhook_delivery_id": str(record.webhook_delivery_id), "transition": record.transition,
                "provider": record.provider, "error_code": record.last_error_code,
            }, created_at=now,
        ))

    async def _metric(self, tenant_id: uuid.UUID, metric_name: str, value: float, dimensions: dict[str, Any], now: datetime) -> None:
        self.db.add(RuntimeMetricSample(tenant_id=tenant_id, metric_name=metric_name, value=value, dimensions=dimensions, recorded_at=now))

    async def _audit(self, instance: RuntimeAlertInstance, action: str, outcome: str, details: dict[str, Any], now: datetime) -> None:
        self.db.add(RuntimeOperationAudit(
            tenant_id=instance.tenant_id, actor=self.actor, action=action, resource_type="alert",
            resource_id=str(instance.id), outcome=outcome, details=details, created_at=now,
        ))


__all__ = ["AlertLifecycleService"]
