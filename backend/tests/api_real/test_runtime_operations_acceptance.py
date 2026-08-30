"""Phase 2.10-H Runtime Operations real PostgreSQL acceptance.

Verifies overview, dimensions, alerts, dead-letter replay and audit facts under tenant isolation.
The test never starts API, Worker, Scheduler, Redis or PostgreSQL services.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from app.infrastructure.db.session import SessionLocal
from app.models.core import Tenant
from app.models.integration_event import IntegrationEventRecord
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_delivery_audit import WebhookDeliveryAudit
from app.models.webhook_integration import WebhookDestination, WebhookSubscription
from app.services.integration.webhook_delivery_repository import WebhookDeliveryRepository
from app.services.runtime_operations import RuntimeOperationsService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_runtime_operations_real_postgres_end_to_end_and_tenant_isolation() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    event_a, event_dead_a, event_b = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    destination_a, destination_b = uuid.uuid4(), uuid.uuid4()
    subscription_a, subscription_b = uuid.uuid4(), uuid.uuid4()
    delivered_id, dead_id, foreign_dead_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-ops-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-ops-b-{suffix}", status="active"),
                WebhookDestination(id=destination_a, tenant_id=tenant_a, name=f"ops-a-{suffix}", endpoint_url="https://example.invalid/a", headers={}, enabled=True),
                WebhookDestination(id=destination_b, tenant_id=tenant_b, name=f"ops-b-{suffix}", endpoint_url="https://example.invalid/b", headers={}, enabled=True),
                WebhookSubscription(id=subscription_a, tenant_id=tenant_a, destination_id=destination_a, event_type="orders.completed", priority=1, enabled=True, filter_config={}),
                WebhookSubscription(id=subscription_b, tenant_id=tenant_b, destination_id=destination_b, event_type="orders.completed", priority=1, enabled=True, filter_config={}),
                IntegrationEventRecord(id=event_a, tenant_id=tenant_a, event_type="orders.completed", schema_version=1, source="acceptance", subject="order:a", idempotency_key=f"ops-a-{suffix}", occurred_at=now, request_id=f"req-a-{suffix}", trace_id=f"trace-a-{suffix}", payload={"fixture": suffix, "delivery": "delivered"}, metadata_json={}, status="published", attempt_count=0),
                IntegrationEventRecord(id=event_dead_a, tenant_id=tenant_a, event_type="orders.completed", schema_version=1, source="acceptance", subject="order:a-dead", idempotency_key=f"ops-a-dead-{suffix}", occurred_at=now, request_id=f"req-a-dead-{suffix}", trace_id=f"trace-a-dead-{suffix}", payload={"fixture": suffix, "delivery": "dead_letter"}, metadata_json={}, status="published", attempt_count=0),
                IntegrationEventRecord(id=event_b, tenant_id=tenant_b, event_type="orders.completed", schema_version=1, source="acceptance", subject="order:b", idempotency_key=f"ops-b-{suffix}", occurred_at=now, request_id=f"req-b-{suffix}", trace_id=f"trace-b-{suffix}", payload={"fixture": suffix}, metadata_json={}, status="published", attempt_count=0),
                WebhookDelivery(id=delivered_id, tenant_id=tenant_a, subscription_id=subscription_a, destination_id=destination_a, integration_event_id=event_a, status="delivered", attempt_count=1, last_attempt_at=now - timedelta(seconds=20), delivered_at=now - timedelta(seconds=10)),
                WebhookDelivery(id=dead_id, tenant_id=tenant_a, subscription_id=subscription_a, destination_id=destination_a, integration_event_id=event_dead_a, status="dead_letter", attempt_count=3, last_attempt_at=now - timedelta(seconds=5), last_error_code="HTTP_500", last_error_message="acceptance failure"),
                WebhookDelivery(id=foreign_dead_id, tenant_id=tenant_b, subscription_id=subscription_b, destination_id=destination_b, integration_event_id=event_b, status="dead_letter", attempt_count=3, last_attempt_at=now, last_error_code="HTTP_500", last_error_message="foreign tenant"),
            ])
            await db.commit()

        async with SessionLocal() as db:
            service = RuntimeOperationsService(db)
            overview = await service.overview(tenant_a, window_hours=24)
            assert overview["events"]["total"] == 2
            assert overview["deliveries"]["total"] == 2
            assert overview["deliveries"]["dead_letter_count"] == 1
            assert overview["slo"]["target_percent"] == 99.0
            assert overview["slo"]["delivery_success_percent"] == 50.0
            assert overview["slo"]["error_budget_percent"] == 0.0

            dimensions = await service.dimension_metrics(tenant_a, window_hours=24)
            assert len(dimensions["items"]) == 1
            assert dimensions["items"][0]["event_type"] == "orders.completed"
            assert dimensions["items"][0]["provider"] == "webhook_http"
            assert dimensions["items"][0]["destination_id"] == destination_a

            alerts = await service.alerts(tenant_a, window_hours=24)
            assert {item["code"] for item in alerts["items"]} == {"delivery_slo_breach", "dead_letter_present", "delivery_retry_present"}

            page, page_size, total, rows = await service.dead_letters(tenant_a, page=1, page_size=20)
            assert (page, page_size, total) == (1, 20, 1)
            assert [row.id for row in rows] == [dead_id]

            replayed = await WebhookDeliveryRepository().replay(db, tenant_a, dead_id, "phase-2.10-acceptance")
            assert replayed is not None
            assert replayed.status == "pending"
            await db.commit()

            audits = list((await db.execute(select(WebhookDeliveryAudit).where(
                WebhookDeliveryAudit.tenant_id == tenant_a,
                WebhookDeliveryAudit.delivery_id == dead_id,
            ))).scalars().all())
            assert any(audit.action == "replay" for audit in audits)

            foreign = await db.scalar(select(WebhookDelivery).where(
                WebhookDelivery.tenant_id == tenant_a, WebhookDelivery.id == foreign_dead_id,
            ))
            assert foreign is None

            foreign_overview = await service.overview(tenant_b, window_hours=24)
            assert foreign_overview["events"]["total"] == 1
            assert foreign_overview["deliveries"]["total"] == 1
            _, _, foreign_total, foreign_rows = await service.dead_letters(tenant_b, page=1, page_size=20)
            assert foreign_total == 1
            assert [row.id for row in foreign_rows] == [foreign_dead_id]
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(WebhookDeliveryAudit).where(WebhookDeliveryAudit.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WebhookDelivery).where(WebhookDelivery.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WebhookSubscription).where(WebhookSubscription.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WebhookDestination).where(WebhookDestination.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()
