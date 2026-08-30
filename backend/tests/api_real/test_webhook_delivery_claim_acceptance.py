"""Phase 2.10-I Webhook Delivery Claim 的真实 PostgreSQL 并发与租户隔离验收。"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete

from app.infrastructure.db.session import SessionLocal
from app.models.core import Tenant
from app.models.integration_event import IntegrationEventRecord
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_integration import WebhookDestination, WebhookSubscription
from app.services.integration.webhook_delivery_repository import WebhookDeliveryRepository

pytestmark = pytest.mark.real_api


async def _create_delivery(tenant_id: uuid.UUID, suffix: str, consumer_group: str) -> uuid.UUID:
    destination_id = uuid.uuid4()
    subscription_id = uuid.uuid4()
    event_id = uuid.uuid4()
    delivery_id = uuid.uuid4()
    async with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"phase-210-i-claim-{suffix}", status="active"))
        db.add(WebhookDestination(
            id=destination_id, tenant_id=tenant_id, name=f"destination-{suffix}",
            provider="webhook_http", endpoint_url="http://localhost:1/claim",
            secret_ref=f"test://{suffix}", headers={}, enabled=True,
        ))
        db.add(WebhookSubscription(
            id=subscription_id, tenant_id=tenant_id, destination_id=destination_id,
            event_type="runtime.claim", priority=1, enabled=True, filter_config={},
        ))
        db.add(IntegrationEventRecord(
            id=event_id, tenant_id=tenant_id, event_type="runtime.claim", source="acceptance",
            subject=str(delivery_id), idempotency_key=f"claim:{suffix}",
            occurred_at=datetime.now(UTC).replace(tzinfo=None),
            payload={"suffix": suffix}, metadata_json={}, status="pending",
        ))
        db.add(WebhookDelivery(
            id=delivery_id, tenant_id=tenant_id, subscription_id=subscription_id,
            destination_id=destination_id, integration_event_id=event_id,
            consumer_group=consumer_group, status="pending", attempt_count=0,
        ))
        await db.commit()
    return delivery_id


async def _cleanup(tenant_ids: list[uuid.UUID]) -> None:
    async with SessionLocal() as db:
        await db.execute(delete(WebhookDelivery).where(WebhookDelivery.tenant_id.in_(tenant_ids)))
        await db.execute(delete(WebhookSubscription).where(WebhookSubscription.tenant_id.in_(tenant_ids)))
        await db.execute(delete(WebhookDestination).where(WebhookDestination.tenant_id.in_(tenant_ids)))
        await db.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id.in_(tenant_ids)))
        await db.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))
        await db.commit()


@pytest.mark.asyncio
async def test_claim_is_atomic_and_scoped_to_tenant_and_consumer_group() -> None:
    """验证 skip-locked Claim 在并发竞争下只允许一个 Worker 获得同一 Delivery。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    group_a = f"phase-2.10-i-a-{suffix}"
    group_b = f"phase-2.10-i-b-{suffix}"
    delivery_id = await _create_delivery(tenant_a, suffix, group_a)
    other_tenant_delivery = await _create_delivery(tenant_b, f"{suffix}-other", group_a)
    try:
        claimed_event = asyncio.Event()
        release_claim = asyncio.Event()

        async def first_claim() -> uuid.UUID | None:
            async with SessionLocal() as db:
                claimed = await WebhookDeliveryRepository().claim_next(
                    db, datetime.now(UTC).replace(tzinfo=None), f"worker-a-{suffix}",
                    tenant_id=tenant_a, consumer_group=group_a,
                )
                assert claimed is not None
                claimed_event.set()
                await release_claim.wait()
                await db.commit()
                return claimed.id

        async def competing_claim() -> uuid.UUID | None:
            await claimed_event.wait()
            async with SessionLocal() as db:
                claimed = await WebhookDeliveryRepository().claim_next(
                    db, datetime.now(UTC).replace(tzinfo=None), f"worker-b-{suffix}",
                    tenant_id=tenant_a, consumer_group=group_a,
                )
                await db.commit()
                return claimed.id if claimed else None

        first_task = asyncio.create_task(first_claim())
        second_task = asyncio.create_task(competing_claim())
        second_result = await second_task
        release_claim.set()
        first_result = await first_task
        assert first_result == delivery_id
        assert second_result is None

        async with SessionLocal() as db:
            tenant_mismatch = await WebhookDeliveryRepository().claim_next(
                db, datetime.now(UTC).replace(tzinfo=None), f"tenant-b-{suffix}",
                tenant_id=tenant_b, consumer_group=group_a,
            )
            assert tenant_mismatch is not None
            assert tenant_mismatch.id == other_tenant_delivery
            await db.rollback()

            group_mismatch = await WebhookDeliveryRepository().claim_next(
                db, datetime.now(UTC).replace(tzinfo=None), f"group-b-{suffix}",
                tenant_id=tenant_a, consumer_group=group_b,
            )
            assert group_mismatch is None
    finally:
        await _cleanup([tenant_a, tenant_b])
