"""Phase 2.10-I Alert Notification 生命周期真实 PostgreSQL 验收。"""

from __future__ import annotations

import asyncio
import os
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
from app.services.runtime_operations.service import RuntimeOperationsService

pytestmark = pytest.mark.real_api


async def _wait_for(predicate, *, timeout: float = 20.0, interval: float = 0.2) -> None:
    """等待 Scheduler/Worker 通过真实 PostgreSQL 完成状态推进。"""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if await predicate():
            return
        await asyncio.sleep(interval)
    raise AssertionError("Runtime Notification 状态在限定时间内未达到预期")


@pytest.mark.asyncio
async def test_alert_notification_lifecycle_real_postgresql() -> None:
    """验证 Scheduler Alert Evaluation 到 Worker Outcome 的完整租户隔离链路。"""
    if os.getenv("PHASE_210_I_RUNTIME_SERVICES_STARTED") != "1":
        pytest.skip("该验收必须由 Runtime Service 启动 Gate 执行")

    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    rule_id = uuid.uuid4()
    primary_id, fallback_id = uuid.uuid4(), uuid.uuid4()
    subscriptions = [uuid.uuid4() for _ in range(4)]
    receiver_calls: list[str] = []

    async def receiver(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """提供仅用于验收的 loopback HTTP endpoint，primary 固定返回 500。"""
        try:
            request = await reader.readuntil(b"\r\n\r\n")
            path = request.split(b"\r\n", 1)[0].decode("latin1").split(" ", 2)[1]
            receiver_calls.append(path)
            status = 500 if path == "/primary" else 200
            body = b"primary failed" if status == 500 else b"ok"
            writer.write(
                (
                    f"HTTP/1.1 {status} {'Internal Server Error' if status == 500 else 'OK'}\r\n"
                    f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
                ).encode() + body
            )
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(receiver, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    async def notifications() -> list[RuntimeNotificationDelivery]:
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

    async def alert_state() -> str | None:
        async with SessionLocal() as db:
            instance = await db.scalar(
                select(RuntimeAlertInstance).where(
                    RuntimeAlertInstance.tenant_id == tenant_a,
                    RuntimeAlertInstance.rule_id == rule_id,
                )
            )
            return instance.state if instance else None

    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-i-lifecycle-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-i-lifecycle-b-{suffix}", status="active"),
                RuntimeAlertRule(
                    id=rule_id, tenant_id=tenant_a, name=f"lifecycle-{suffix}",
                    metric_name="runtime.test.lifecycle", operator=">", threshold=10,
                    window_minutes=5, severity="critical", enabled=True,
                ),
                WebhookDestination(
                    id=primary_id, tenant_id=tenant_a, name=f"primary-{suffix}",
                    endpoint_url=f"http://127.0.0.1:{port}/primary", secret_ref=f"test://{suffix}/primary",
                    headers={}, enabled=True, provider="webhook_http",
                ),
                WebhookDestination(
                    id=fallback_id, tenant_id=tenant_a, name=f"fallback-{suffix}",
                    endpoint_url=f"http://127.0.0.1:{port}/fallback", secret_ref=f"test://{suffix}/fallback",
                    headers={}, enabled=True, provider="webhook_http_fallback",
                ),
                WebhookSubscription(
                    id=subscriptions[0], tenant_id=tenant_a, destination_id=primary_id,
                    event_type="alert.firing", priority=1, enabled=True, filter_config={},
                ),
                WebhookSubscription(
                    id=subscriptions[1], tenant_id=tenant_a, destination_id=fallback_id,
                    event_type="alert.firing", priority=2, enabled=True, filter_config={},
                ),
                WebhookSubscription(
                    id=subscriptions[2], tenant_id=tenant_a, destination_id=primary_id,
                    event_type="alert.recovery", priority=1, enabled=True, filter_config={},
                ),
                WebhookSubscription(
                    id=subscriptions[3], tenant_id=tenant_a, destination_id=fallback_id,
                    event_type="alert.recovery", priority=2, enabled=True, filter_config={},
                ),
                RuntimeNotificationPolicy(
                    tenant_id=tenant_a, name=f"lifecycle-policy-{suffix}", severity="critical",
                    routing_key=f"alert.lifecycle-{suffix}", destination_ids=[str(primary_id), str(fallback_id)],
                    provider_order=["webhook_http", "webhook_http_fallback"],
                    group_window_seconds=300, cooldown_seconds=3600, escalation=[], enabled=True,
                ),
            ])
            fired = RuntimeMetricSample(
                tenant_id=tenant_a, metric_name="runtime.test.lifecycle", value=20,
                dimensions={}, recorded_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(fired)
            await db.commit()

        await _wait_for(lambda: alert_state() == "firing")

        async def first_cycle_complete() -> bool:
            rows = await notifications()
            return len(rows) == 2 and {row.status for row in rows} == {"dead_letter", "delivered"}

        await _wait_for(first_cycle_complete)
        assert "/primary" in receiver_calls and "/fallback" in receiver_calls

        async with SessionLocal() as db:
            recovered = RuntimeMetricSample(
                tenant_id=tenant_a, metric_name="runtime.test.lifecycle", value=1,
                dimensions={}, recorded_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(recovered)
            await db.commit()

        await _wait_for(lambda: alert_state() == "recovered")

        async def recovery_cycle_complete() -> bool:
            rows = await notifications()
            return len(rows) == 4 and sum(row.status == "delivered" for row in rows) == 2

        await _wait_for(recovery_cycle_complete)

        # 同一 recovery 状态再次评估不会产生第二个 transition/notification。
        async with SessionLocal() as db:
            stable = RuntimeMetricSample(
                tenant_id=tenant_a, metric_name="runtime.test.lifecycle", value=1,
                dimensions={}, recorded_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(stable)
            await db.commit()
        await asyncio.sleep(1.0)
        assert len(await notifications()) == 4

        async with SessionLocal() as db:
            group = await db.scalar(select(RuntimeNotificationGroup).where(RuntimeNotificationGroup.tenant_id == tenant_a))
            assert group is not None and group.event_count == 2

            overview = await RuntimeOperationsService(db).overview(tenant_a, window_hours=24)
            assert overview["notifications"]["total"] == 4
            assert "slo" in overview["notifications"]

            metrics = await RuntimeOperationsService(db).notification_metrics(tenant_a, window_hours=24)
            assert {item["provider"] for item in metrics["items"]} >= {"webhook_http", "webhook_http_fallback"}

            audits = list((await db.execute(
                select(RuntimeOperationAudit).where(
                    RuntimeOperationAudit.tenant_id == tenant_a,
                    RuntimeOperationAudit.action.in_([
                        "notification.delivery.dead_letter",
                        "notification.delivery.delivered",
                        "notification.fallback.routed",
                        "notification.route",
                    ]),
                )
            )).scalars().all())
            assert {audit.action for audit in audits} >= {
                "notification.delivery.dead_letter",
                "notification.delivery.delivered",
                "notification.fallback.routed",
                "notification.route",
            }

            assert list((await db.execute(
                select(RuntimeNotificationDelivery).where(RuntimeNotificationDelivery.tenant_id == tenant_b)
            )).scalars().all()) == []
    finally:
        server.close()
        await server.wait_closed()
        async with SessionLocal() as db:
            for model in [RuntimeOperationAudit, RuntimeMetricSample, RuntimeNotificationDelivery,
                          RuntimeNotificationGroup, RuntimeAlertInstance, RuntimeNotificationPolicy,
                          WebhookDelivery, WebhookSubscription, WebhookDestination,
                          IntegrationEventRecord, RuntimeAlertRule, Tenant]:
                await db.execute(delete(model).where(model.tenant_id.in_([tenant_a, tenant_b])))
            await db.commit()
