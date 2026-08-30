"""Phase 2.10-I Alert -> Notification -> Worker real PostgreSQL acceptance."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select

from app.infrastructure.db.session import SessionLocal
from app.models.core import Tenant
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
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_integration import WebhookDestination, WebhookSubscription
from app.services.integration.alert_lifecycle import AlertLifecycleService
from app.services.integration.webhook_delivery import WebhookDeliveryWorker

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_alert_notification_worker_delivery_fallback_and_slo_are_tenant_scoped() -> None:
    suffix = uuid.uuid4().hex[:12]
    consumer_group = f"phase-2.10-i-{suffix}"
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    rule_id = uuid.uuid4()
    destination_a = uuid.uuid4()
    destination_b = uuid.uuid4()
    subscription_a = uuid.uuid4()
    subscription_b = uuid.uuid4()
    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-i-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-i-b-{suffix}", status="active"),
                RuntimeAlertRule(
                    id=rule_id, tenant_id=tenant_a, name=f"delivery-{suffix}", metric_name="runtime.test",
                    operator=">", threshold=10, window_minutes=5, severity="critical", enabled=True,
                ),
                WebhookDestination(
                    id=destination_a, tenant_id=tenant_a, name=f"primary-{suffix}",
                    endpoint_url="http://localhost:1/primary", secret_ref=f"test://{suffix}-a", headers={},
                    enabled=True, provider="webhook_http",
                ),
                WebhookDestination(
                    id=destination_b, tenant_id=tenant_a, name=f"fallback-{suffix}",
                    endpoint_url="http://localhost:1/fallback", secret_ref=f"test://{suffix}-b", headers={},
                    enabled=True, provider="webhook_http_fallback",
                ),
                WebhookSubscription(
                    id=subscription_a, tenant_id=tenant_a, destination_id=destination_a,
                    event_type="alert.firing", priority=1, enabled=True, filter_config={},
                ),
                WebhookSubscription(
                    id=subscription_b, tenant_id=tenant_a, destination_id=destination_b,
                    event_type="alert.firing", priority=2, enabled=True, filter_config={},
                ),
                RuntimeNotificationPolicy(
                    tenant_id=tenant_a, name=f"critical-{suffix}", severity="critical",
                    routing_key=f"alert.delivery-{suffix}", destination_ids=[str(destination_a), str(destination_b)],
                    provider_order=["webhook_http", "webhook_http_fallback"], group_window_seconds=60,
                    cooldown_seconds=0, escalation=[], enabled=True,
                ),
            ])
            await db.flush()
            rule = await db.get(RuntimeAlertRule, rule_id)
            assert rule is not None
            sample = RuntimeMetricSample(
                tenant_id=tenant_a, metric_name="runtime.test", value=20, dimensions={},
                recorded_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(sample)
            await db.flush()
            lifecycle = AlertLifecycleService(
                db, actor=f"acceptance-{suffix}", consumer_group=consumer_group,
            )
            instance = await lifecycle.evaluate_rule(rule, sample, now=sample.recorded_at)
            await db.commit()

        async with SessionLocal() as db:
            deliveries = list((await db.execute(
                select(WebhookDelivery).where(WebhookDelivery.tenant_id == tenant_a).order_by(WebhookDelivery.created_at)
            )).scalars().all())
            notifications = list((await db.execute(
                select(RuntimeNotificationDelivery).where(RuntimeNotificationDelivery.tenant_id == tenant_a)
            )).scalars().all())
            assert len(deliveries) == 1
            assert len(notifications) == 1
            assert deliveries[0].consumer_group == consumer_group
            assert notifications[0].provider == "webhook_http"
            assert notifications[0].status == "planned"
            assert notifications[0].alert_instance_id == instance.id

        calls = 0

        async def sender(record: WebhookDelivery, context: dict) -> int:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("primary provider failure")
            return 200

        first = WebhookDeliveryWorker(
            owner=f"acceptance-primary-{suffix}", sender=sender, max_attempts=1,
            tenant_id=tenant_a, consumer_group=consumer_group,
        )
        assert await first.deliver_once() is True

        async with SessionLocal() as db:
            first_delivery = await db.scalar(select(WebhookDelivery).where(WebhookDelivery.tenant_id == tenant_a))
            assert first_delivery is not None
            assert first_delivery.status == "dead_letter"
            assert first_delivery.consumer_group == consumer_group
            first_notification = await db.scalar(select(RuntimeNotificationDelivery).where(
                RuntimeNotificationDelivery.webhook_delivery_id == first_delivery.id,
            ))
            assert first_notification is not None
            assert first_notification.status == "dead_letter"
            fallback = await db.scalar(select(RuntimeNotificationDelivery).where(
                RuntimeNotificationDelivery.tenant_id == tenant_a,
                RuntimeNotificationDelivery.webhook_delivery_id != first_delivery.id,
            ))
            assert fallback is not None
            assert fallback.provider == "webhook_http_fallback"
            assert fallback.status == "planned"
            fallback_delivery = await db.get(WebhookDelivery, fallback.webhook_delivery_id)
            assert fallback_delivery is not None
            assert fallback_delivery.consumer_group == consumer_group

        second = WebhookDeliveryWorker(
            owner=f"acceptance-fallback-{suffix}", sender=sender, max_attempts=1,
            tenant_id=tenant_a, consumer_group=consumer_group,
        )
        assert await second.deliver_once() is True

        async with SessionLocal() as db:
            notification_rows = list((await db.execute(
                select(RuntimeNotificationDelivery).where(RuntimeNotificationDelivery.tenant_id == tenant_a)
            )).scalars().all())
            assert {item.status for item in notification_rows} == {"dead_letter", "delivered"}
            metrics = list((await db.execute(
                select(RuntimeMetricSample).where(
                    RuntimeMetricSample.tenant_id == tenant_a,
                    RuntimeMetricSample.metric_name.in_([
                        "notification.delivery.dead_letter",
                        "notification.delivery.delivered",
                    ]),
                )
            )).scalars().all())
            assert {item.metric_name for item in metrics} == {
                "notification.delivery.dead_letter", "notification.delivery.delivered",
            }
            audits = list((await db.execute(
                select(RuntimeOperationAudit).where(
                    RuntimeOperationAudit.tenant_id == tenant_a,
                    RuntimeOperationAudit.action.in_([
                        "notification.delivery.dead_letter",
                        "notification.delivery.delivered",
                        "notification.fallback.routed",
                    ]),
                )
            )).scalars().all()
            assert {item.action for item in audits} >= {
                "notification.delivery.dead_letter", "notification.delivery.delivered", "notification.fallback.routed",
            }
            other_tenant = list((await db.execute(
                select(RuntimeNotificationDelivery).where(RuntimeNotificationDelivery.tenant_id == tenant_b)
            )).scalars().all())
            assert other_tenant == []
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(RuntimeOperationAudit).where(RuntimeOperationAudit.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(RuntimeMetricSample).where(RuntimeMetricSample.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(RuntimeNotificationDelivery).where(RuntimeNotificationDelivery.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(RuntimeNotificationGroup).where(RuntimeNotificationGroup.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(RuntimeAlertInstance).where(RuntimeAlertInstance.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(RuntimeNotificationPolicy).where(RuntimeNotificationPolicy.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WebhookDelivery).where(WebhookDelivery.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WebhookSubscription).where(WebhookSubscription.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WebhookDestination).where(WebhookDestination.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(RuntimeAlertRule).where(RuntimeAlertRule.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()
