"""Phase 2.10-I fallback exhausted 真实 PostgreSQL 验收。

职责：验证主 Provider 进入 dead-letter 后没有可用 fallback 时，Notification DLQ、SLO Metric 与 Operational Audit 一致落库。
边界：不启动服务，不执行外部网络请求；测试数据由用例自动创建并清理。
"""

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
async def test_fallback_exhausted_persists_dlq_slo_and_audit() -> None:
    """验证 fallback 耗尽后的 Notification DLQ / Metric / Audit 事实保持同一租户边界。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_id = uuid.uuid4()
    rule_id = uuid.uuid4()
    destination_id = uuid.uuid4()
    subscription_id = uuid.uuid4()
    consumer_group = f"phase-2.10-i-dlq-{suffix}"
    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_id, name=f"phase-210-i-dlq-{suffix}", status="active"),
                RuntimeAlertRule(
                    id=rule_id,
                    tenant_id=tenant_id,
                    name=f"dlq-{suffix}",
                    metric_name="runtime.test",
                    operator=">",
                    threshold=10,
                    window_minutes=5,
                    severity="critical",
                    enabled=True,
                ),
                WebhookDestination(
                    id=destination_id,
                    tenant_id=tenant_id,
                    name=f"primary-{suffix}",
                    endpoint_url="http://localhost:1/primary",
                    secret_ref=f"test://{suffix}",
                    headers={},
                    enabled=True,
                    provider="webhook_http",
                ),
                WebhookSubscription(
                    id=subscription_id,
                    tenant_id=tenant_id,
                    destination_id=destination_id,
                    event_type="alert.firing",
                    priority=1,
                    enabled=True,
                    filter_config={},
                ),
                RuntimeNotificationPolicy(
                    tenant_id=tenant_id,
                    name=f"critical-{suffix}",
                    severity="critical",
                    routing_key=f"alert.dlq-{suffix}",
                    destination_ids=[str(destination_id)],
                    provider_order=["webhook_http"],
                    group_window_seconds=60,
                    cooldown_seconds=0,
                    escalation=[],
                    enabled=True,
                ),
            ])
            await db.flush()
            rule = await db.get(RuntimeAlertRule, rule_id)
            assert rule is not None
            sample = RuntimeMetricSample(
                tenant_id=tenant_id,
                metric_name="runtime.test",
                value=20,
                dimensions={},
                recorded_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(sample)
            await db.flush()
            lifecycle = AlertLifecycleService(
                db,
                actor=f"acceptance-{suffix}",
                consumer_group=consumer_group,
            )
            instance = await lifecycle.evaluate_rule(rule, sample, now=sample.recorded_at)
            assert instance is not None
            await db.commit()

        async def sender(record: WebhookDelivery, context: dict) -> int:
            """模拟唯一 Provider 永久失败，禁止产生真实网络请求。"""
            raise RuntimeError("primary provider failure")

        worker = WebhookDeliveryWorker(
            owner=f"acceptance-dlq-{suffix}",
            sender=sender,
            max_attempts=1,
            tenant_id=tenant_id,
            consumer_group=consumer_group,
        )
        assert await worker.deliver_once() is True

        async with SessionLocal() as db:
            delivery = await db.scalar(
                select(WebhookDelivery).where(WebhookDelivery.tenant_id == tenant_id)
            )
            assert delivery is not None
            assert delivery.status == "dead_letter"
            assert delivery.consumer_group == consumer_group

            notifications = list(
                (
                    await db.execute(
                        select(RuntimeNotificationDelivery).where(
                            RuntimeNotificationDelivery.tenant_id == tenant_id
                        )
                    )
                ).scalars().all()
            )
            assert len(notifications) == 1
            assert notifications[0].status == "dead_letter"

            metrics = list(
                (
                    await db.execute(
                        select(RuntimeMetricSample).where(
                            RuntimeMetricSample.tenant_id == tenant_id,
                            RuntimeMetricSample.metric_name == "notification.dlq",
                        )
                    )
                ).scalars().all()
            )
            assert len(metrics) == 1
            assert metrics[0].value == 1
            assert metrics[0].dimensions["provider"] == "webhook_http"

            audits = list(
                (
                    await db.execute(
                        select(RuntimeOperationAudit).where(
                            RuntimeOperationAudit.tenant_id == tenant_id,
                            RuntimeOperationAudit.action == "notification.fallback.exhausted",
                        )
                    )
                ).scalars().all()
            )
            assert len(audits) == 1
            assert audits[0].outcome == "failure"

            groups = list(
                (
                    await db.execute(
                        select(RuntimeNotificationGroup).where(
                            RuntimeNotificationGroup.tenant_id == tenant_id
                        )
                    )
                ).scalars().all()
            )
            assert len(groups) == 1
            assert groups[0].severity == "critical"
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(RuntimeOperationAudit).where(RuntimeOperationAudit.tenant_id == tenant_id))
            await db.execute(delete(RuntimeMetricSample).where(RuntimeMetricSample.tenant_id == tenant_id))
            await db.execute(delete(RuntimeNotificationDelivery).where(RuntimeNotificationDelivery.tenant_id == tenant_id))
            await db.execute(delete(RuntimeNotificationGroup).where(RuntimeNotificationGroup.tenant_id == tenant_id))
            await db.execute(delete(RuntimeAlertInstance).where(RuntimeAlertInstance.tenant_id == tenant_id))
            await db.execute(delete(RuntimeNotificationPolicy).where(RuntimeNotificationPolicy.tenant_id == tenant_id))
            await db.execute(delete(WebhookDelivery).where(WebhookDelivery.tenant_id == tenant_id))
            await db.execute(delete(WebhookSubscription).where(WebhookSubscription.tenant_id == tenant_id))
            await db.execute(delete(WebhookDestination).where(WebhookDestination.tenant_id == tenant_id))
            await db.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id == tenant_id))
            await db.execute(delete(RuntimeAlertRule).where(RuntimeAlertRule.tenant_id == tenant_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()
