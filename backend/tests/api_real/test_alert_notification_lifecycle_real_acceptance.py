"""Phase 2.10-I Alert Notification 生命周期真实 PostgreSQL 验收。

测试边界：服务启动由 Gate 脚本负责；本测试只创建租户隔离的临时事实，并等待真实 Worker
通过本地 loopback HTTP Provider 完成投递。禁止手工填写 tenant、destination 或凭据。
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

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
from app.services.runtime_operations.service import RuntimeOperationsService

pytestmark = pytest.mark.real_api


async def _wait_for(predicate, *, timeout: float = 15.0, interval: float = 0.2) -> None:
    """等待真实 Worker 完成持久化状态变化，超时即失败。"""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if await predicate():
            return
        await asyncio.sleep(interval)
    raise AssertionError("Runtime Notification 状态在限定时间内未达到预期")


@pytest.mark.asyncio
async def test_alert_notification_lifecycle_real_postgresql() -> None:
    """验证 firing/recovery、grouping/dedup、Provider fallback、DLQ、SLO 与 Audit 全链路。"""
    if os.getenv("PHASE_210_I_RUNTIME_SERVICES_STARTED") != "1":
        pytest.skip("该验收必须由 Runtime Service 启动 Gate 执行")

    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    rule_id = uuid.uuid4()
    primary_id, fallback_id = uuid.uuid4(), uuid.uuid4()
    primary_sub_id, fallback_sub_id = uuid.uuid4(), uuid.uuid4()
    primary_recovery_sub_id, fallback_recovery_sub_id = uuid.uuid4(), uuid.uuid4()
    receiver_calls: list[str] = []

    async def receiver(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """提供仅用于本地验收的 loopback HTTP Provider 端点。"""
        try:
            request = await reader.readuntil(b"\r\n\r\n")
            first_line = request.split(b"\r\n", 1)[0].decode("latin1")
            path = first_line.split(" ", 2)[1]
            receiver_calls.append(path)
            status = 500 if path == "/primary" else 200
            body = b"ok" if status == 200 else b"primary failed"
            response = (
                f"HTTP/1.1 {status} {'OK' if status == 200 else 'Internal Server Error'}\r\n"
                f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
            ).encode() + body
            writer.write(response)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(receiver, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    async def notification_rows() -> list[RuntimeNotificationDelivery]:
        async with SessionLocal() as db:
            return list(
                (
                    await db.execute(
                        select(RuntimeNotificationDelivery)
                        .where(RuntimeNotificationDelivery.tenant_id == tenant_a)
                        .order_by(RuntimeNotificationDelivery.created_at, RuntimeNotificationDelivery.id)
                    )
                ).scalars().all()
            )

    try:
        async with SessionLocal() as db:
            db.add_all(
                [
                    Tenant(id=tenant_a, name=f"phase-210-i-lifecycle-a-{suffix}", status="active"),
                    Tenant(id=tenant_b, name=f"phase-210-i-lifecycle-b-{suffix}", status="active"),
                    RuntimeAlertRule(
                        id=rule_id,
                        tenant_id=tenant_a,
                        name=f"lifecycle-{suffix}",
                        metric_name="runtime.test.lifecycle",
                        operator=">",
                        threshold=10,
                        window_minutes=5,
                        severity="critical",
                        enabled=True,
                    ),
                    WebhookDestination(
                        id=primary_id,
                        tenant_id=tenant_a,
                        name=f"primary-{suffix}",
                        endpoint_url=f"http://127.0.0.1:{port}/primary",
                        secret_ref=f"test://{suffix}/primary",
                        headers={},
                        enabled=True,
                        provider="webhook_http",
                    ),
                    WebhookDestination(
                        id=fallback_id,
                        tenant_id=tenant_a,
                        name=f"fallback-{suffix}",
                        endpoint_url=f"http://127.0.0.1:{port}/fallback",
                        secret_ref=f"test://{suffix}/fallback",
                        headers={},
                        enabled=True,
                        provider="webhook_http_fallback",
                    ),
                    WebhookSubscription(
                        id=primary_sub_id,
                        tenant_id=tenant_a,
                        destination_id=primary_id,
                        event_type="alert.firing",
                        priority=1,
                        enabled=True,
                        filter_config={},
                    ),
                    WebhookSubscription(
                        id=fallback_sub_id,
                        tenant_id=tenant_a,
                        destination_id=fallback_id,
                        event_type="alert.firing",
                        priority=2,
                        enabled=True,
                        filter_config={},
                    ),
                    WebhookSubscription(
                        id=primary_recovery_sub_id,
                        tenant_id=tenant_a,
                        destination_id=primary_id,
                        event_type="alert.recovery",
                        priority=1,
                        enabled=True,
                        filter_config={},
                    ),
                    WebhookSubscription(
                        id=fallback_recovery_sub_id,
                        tenant_id=tenant_a,
                        destination_id=fallback_id,
                        event_type="alert.recovery",
                        priority=2,
                        enabled=True,
                        filter_config={},
                    ),
                    RuntimeNotificationPolicy(
                        tenant_id=tenant_a,
                        name=f"lifecycle-policy-{suffix}",
                        severity="critical",
                        routing_key=f"alert.lifecycle-{suffix}",
                        destination_ids=[str(primary_id), str(fallback_id)],
                        provider_order=["webhook_http", "webhook_http_fallback"],
                        group_window_seconds=300,
                        cooldown_seconds=3600,
                        escalation=[],
                        enabled=True,
                    ),
                ]
            )
            await db.flush()
            rule = await db.get(RuntimeAlertRule, rule_id)
            assert rule is not None
            fired_at = datetime.now(UTC).replace(tzinfo=None)
            fired_sample = RuntimeMetricSample(
                tenant_id=tenant_a,
                metric_name=rule.metric_name,
                value=20,
                dimensions={},
                recorded_at=fired_at,
            )
            db.add(fired_sample)
            await db.flush()
            instance = await AlertLifecycleService(db, actor=f"acceptance-{suffix}").evaluate_rule(
                rule, fired_sample, now=fired_at
            )
            assert instance.state == "firing"
            await db.commit()

        async def first_cycle_complete() -> bool:
            rows = await notification_rows()
            return len(rows) == 2 and {row.status for row in rows} == {"dead_letter", "delivered"}

        await _wait_for(first_cycle_complete)

        async with SessionLocal() as db:
            rows = await notification_rows()
            assert len(rows) == 2
            assert {row.provider for row in rows} == {"webhook_http", "webhook_http_fallback"}
            assert "/primary" in receiver_calls and "/fallback" in receiver_calls

            rule = await db.get(RuntimeAlertRule, rule_id)
            assert rule is not None
            recovered_at = datetime.now(UTC).replace(tzinfo=None)
            recovery_sample = RuntimeMetricSample(
                tenant_id=tenant_a,
                metric_name=rule.metric_name,
                value=1,
                dimensions={},
                recorded_at=recovered_at,
            )
            db.add(recovery_sample)
            await db.flush()
            instance = await db.scalar(
                select(RuntimeAlertInstance).where(RuntimeAlertInstance.tenant_id == tenant_a, RuntimeAlertInstance.rule_id == rule_id)
            )
            assert instance is not None
            updated = await AlertLifecycleService(db, actor=f"acceptance-{suffix}").evaluate_rule(
                rule, recovery_sample, now=recovered_at
            )
            assert updated.state == "recovered"
            await db.commit()

        async def recovery_cycle_complete() -> bool:
            rows = await notification_rows()
            return len(rows) == 4 and sum(row.status == "delivered" for row in rows) == 2

        await _wait_for(recovery_cycle_complete)

        async with SessionLocal() as db:
            # 同一次 recovery 再评估不产生第二次 transition，验证生命周期幂等。
            rule = await db.get(RuntimeAlertRule, rule_id)
            assert rule is not None
            stable_sample = RuntimeMetricSample(
                tenant_id=tenant_a,
                metric_name=rule.metric_name,
                value=1,
                dimensions={},
                recorded_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(stable_sample)
            await db.flush()
            instance = await db.scalar(
                select(RuntimeAlertInstance).where(RuntimeAlertInstance.tenant_id == tenant_a, RuntimeAlertInstance.rule_id == rule_id)
            )
            assert instance is not None
            await AlertLifecycleService(db, actor=f"acceptance-{suffix}").evaluate_rule(rule, stable_sample)
            await db.commit()

        assert len(await notification_rows()) == 4

        async with SessionLocal() as db:
            group = await db.scalar(
                select(RuntimeNotificationGroup).where(RuntimeNotificationGroup.tenant_id == tenant_a)
            )
            assert group is not None
            assert group.event_count == 2

            overview = await RuntimeOperationsService(db).overview(tenant_a, window_hours=24)
            assert "notifications" in overview
            assert overview["notifications"]["total"] == 4
            assert "slo" in overview["notifications"]

            metrics = await RuntimeOperationsService(db).notification_metrics(tenant_a, window_hours=24)
            assert {item["provider"] for item in metrics["items"]} >= {"webhook_http", "webhook_http_fallback"}

            audits = list(
                (
                    await db.execute(
                        select(RuntimeOperationAudit).where(
                            RuntimeOperationAudit.tenant_id == tenant_a,
                            RuntimeOperationAudit.action.in_(
                                [
                                    "notification.delivery.dead_letter",
                                    "notification.delivery.delivered",
                                    "notification.fallback.routed",
                                    "notification.route",
                                ]
                            ),
                        )
                    )
                ).scalars().all()
            )
            assert {audit.action for audit in audits} >= {
                "notification.delivery.dead_letter",
                "notification.delivery.delivered",
                "notification.fallback.routed",
                "notification.route",
            }

            tenant_b_rows = list(
                (
                    await db.execute(
                        select(RuntimeNotificationDelivery).where(RuntimeNotificationDelivery.tenant_id == tenant_b)
                    )
                ).scalars().all()
            )
            assert tenant_b_rows == []

    finally:
        server.close()
        await server.wait_closed()
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
