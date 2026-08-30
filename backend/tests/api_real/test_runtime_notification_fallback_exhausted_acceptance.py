"""Phase 2.10-I fallback exhausted 真实 PostgreSQL 验收。

职责：验证主 Provider 进入 dead-letter 后没有可用 fallback 时，Notification DLQ、SLO、Canonical Metrics 与 Operational Audit 一致落库。
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
from app.services.runtime_operations import RuntimeMetricContract, RuntimeOperationsService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_fallback_exhausted_persists_dlq_slo_metrics_and_audit() -> None:
    """验证 fallback 耗尽后的 Notification DLQ / SLO / canonical Metric / Audit 事实保持同一租户边界。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_id = uuid.uuid4()
    foreign_tenant_id = uuid.uuid4()
    rule_id = uuid.uuid4()
    destination_id = uuid.uuid4()
    subscription_id = uuid.uuid4()
    consumer_group = f"phase-2.10-i-dlq-{suffix}"
    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_id, name=f"phase-210-i-dlq-{suffix}", status="active"),
                Tenant(id=foreign_tenant_id, name=f"phase-210-i-foreign-{suffix}", status="active"),
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
            assert notifications[0].provider == "webhook_http"

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
            assert metrics[0].dimensions["transition"] == "firing"

            operations = RuntimeOperationsService(db)
            overview = await operations.overview(tenant_id, window_hours=24)
            assert overview["notifications"]["dead_letter_count"] == 1
            assert overview["notifications"]["slo"]["delivery_success_percent"] == 0.0
            assert overview["notifications"]["slo"]["target_percent"] == 99.0
            assert overview["notifications"]["slo"]["error_budget_percent"] == 0.0

            canonical_values = {
                "runtime.delivery.success_percent": overview["slo"]["delivery_success_percent"],
                "runtime.delivery.retry_count": overview["deliveries"]["retry_count"],
                "runtime.delivery.dead_letter_count": overview["deliveries"]["dead_letter_count"],
            }
            prometheus = RuntimeMetricContract.prometheus(tenant_id, canonical_values)
            assert "runtime_delivery_success_percent" in prometheus
            assert "runtime_delivery_retry_count" in prometheus
            assert "runtime_delivery_dead_letter_count" in prometheus
            assert f'tenant_id="{tenant_id}"' in prometheus
            assert str(foreign_tenant_id) not in prometheus

            otlp = RuntimeMetricContract.otlp(tenant_id, canonical_values)
            resource_attributes = {
                item["key"]: item["value"]["stringValue"]
                for item in otlp["resourceMetrics"][0]["resource"]["attributes"]
            }
            assert resource_attributes["tenant.id"] == str(tenant_id)
            exported_names = [
                item["name"]
                for item in otlp["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
            ]
            assert exported_names == list(canonical_values)
            assert set(exported_names).issubset(RuntimeMetricContract.OTLP_NAMES)

            audits = list(
                (
                    await db.execute(
                        select(RuntimeOperationAudit)
                        .where(
                            RuntimeOperationAudit.tenant_id == tenant_id,
                            RuntimeOperationAudit.resource_id == str(instance.id),
                        )
                        .order_by(RuntimeOperationAudit.created_at, RuntimeOperationAudit.id)
                    )
                ).scalars().all()
            )
            actions = [audit.action for audit in audits]
            assert "notification.delivery.dead_letter" in actions
            assert "notification.fallback.exhausted" in actions
            exhausted = next(audit for audit in audits if audit.action == "notification.fallback.exhausted")
            assert exhausted.outcome == "failure"
            assert exhausted.details["provider"] == "webhook_http"
            assert exhausted.tenant_id == tenant_id
            assert await operations.audit_list(foreign_tenant_id) == []

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
            await db.execute(delete(RuntimeOperationAudit).where(RuntimeOperationAudit.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(RuntimeMetricSample).where(RuntimeMetricSample.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(RuntimeNotificationDelivery).where(RuntimeNotificationDelivery.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(RuntimeNotificationGroup).where(RuntimeNotificationGroup.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(RuntimeAlertInstance).where(RuntimeAlertInstance.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(RuntimeNotificationPolicy).where(RuntimeNotificationPolicy.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(WebhookDelivery).where(WebhookDelivery.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(WebhookSubscription).where(WebhookSubscription.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(WebhookDestination).where(WebhookDestination.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(RuntimeAlertRule).where(RuntimeAlertRule.tenant_id.in_([tenant_id, foreign_tenant_id])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_id, foreign_tenant_id])))
            await db.commit()
