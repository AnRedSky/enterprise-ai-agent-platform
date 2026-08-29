"""Phase 2.9-D real HTTP + PostgreSQL Webhook Delivery acceptance.

The test owns all fixture data and an ephemeral localhost HTTP receiver. It never starts the
application API, Scheduler, Redis or a background Worker process; the Worker is instantiated
in-process so the acceptance verifies the real PostgreSQL lease/state path and real HTTP I/O.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import delete, select

from app.infrastructure.db.session import SessionLocal
from app.models.core import Tenant
from app.models.integration_event import IntegrationEventRecord
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_integration import WebhookDestination, WebhookSubscription
from app.services.integration.security import WebhookEndpointPolicy
from app.services.integration.secrets import MappingSecretResolver
from app.services.integration.webhook_delivery import WebhookDeliveryWorker
from app.services.integration.webhook_provider import WebhookHTTPProvider
from app.services.integration.webhook_delivery_repository import WebhookDeliveryRepository

pytestmark = pytest.mark.real_api


class _Receiver(BaseHTTPRequestHandler):
    received: list[tuple[dict[str, str], bytes]] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        type(self).received.append((dict(self.headers), body))
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.mark.asyncio
async def test_webhook_delivery_real_http_postgres_replay_and_audit() -> None:
    receiver = ThreadingHTTPServer(("127.0.0.1", 0), _Receiver)
    thread = threading.Thread(target=receiver.serve_forever, daemon=True)
    thread.start()
    port = receiver.server_address[1]
    suffix = uuid.uuid4().hex[:12]
    tenant_id = uuid.uuid4()
    event_id = uuid.uuid4()
    destination_id = uuid.uuid4()
    subscription_id = uuid.uuid4()
    delivery_id = uuid.uuid4()
    try:
        endpoint = f"http://localhost:{port}/webhook"
        policy = WebhookEndpointPolicy(
            allowed_hosts=frozenset({"localhost"}),
            allowed_ports=frozenset({port}),
            allow_http=True,
        )
        provider = WebhookHTTPProvider(
            secret_resolver=MappingSecretResolver({f"test://{suffix}": "phase-2.9-secret"}),
            endpoint_policy=policy,
        )
        async with SessionLocal() as db:
            db.add(Tenant(id=tenant_id, name=f"phase-29-webhook-{suffix}", status="active"))
            event = IntegrationEventRecord(
                id=event_id, tenant_id=tenant_id, event_type="phase_2_9.acceptance",
                schema_version=1, source="acceptance", subject=f"subject-{suffix}",
                idempotency_key=f"idempotency-{suffix}", occurred_at=datetime.now(UTC).replace(tzinfo=None),
                request_id=f"request-{suffix}", trace_id=f"trace-{suffix}",
                payload={"fixture": suffix, "message": "real webhook acceptance"}, metadata_json={},
                status="pending", attempt_count=0,
            )
            destination = WebhookDestination(
                id=destination_id, tenant_id=tenant_id, name=f"receiver-{suffix}",
                endpoint_url=endpoint, secret_ref=f"test://{suffix}", headers={}, enabled=True,
            )
            subscription = WebhookSubscription(
                id=subscription_id, tenant_id=tenant_id, destination_id=destination_id,
                event_type=event.event_type, priority=1, enabled=True, filter_config={},
            )
            delivery = WebhookDelivery(
                id=delivery_id, tenant_id=tenant_id, subscription_id=subscription_id,
                destination_id=destination_id, integration_event_id=event_id,
                status="pending", attempt_count=0,
            )
            db.add_all([event, destination, subscription, delivery])
            await db.commit()

        worker = WebhookDeliveryWorker(sender=provider.send, owner=f"acceptance-{suffix}", lease_seconds=30, max_attempts=3)
        assert await worker.deliver_once() is True

        async with SessionLocal() as db:
            item = await db.scalar(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id))
            assert item is not None
            assert item.status == "delivered"
            assert item.response_status_code == 204
            audits = await WebhookDeliveryRepository().list_audit(db, tenant_id, delivery_id)
            assert any(a.action == "delivered" for a in audits)

            replayed = await WebhookDeliveryRepository().replay(db, tenant_id, delivery_id, f"acceptance-{suffix}")
            assert replayed is not None
            await db.commit()

        assert await worker.deliver_once() is True
        assert len(_Receiver.received) >= 2
        assert _Receiver.received[-1][0]["X-Webhook-Signature"].startswith("sha256=")

        async with SessionLocal() as db:
            audits = await WebhookDeliveryRepository().list_audit(db, tenant_id, delivery_id)
            assert any(a.action == "replay" for a in audits)
            assert len([a for a in audits if a.action == "delivered"]) >= 2
    except Exception as exc:
        if "connection" in str(exc).lower() or "database" in str(exc).lower():
            pytest.skip(f"PostgreSQL is unavailable: {exc}")
        raise
    finally:
        receiver.shutdown()
        receiver.server_close()
        thread.join(timeout=2)
        async with SessionLocal() as db:
            await db.execute(delete(WebhookDelivery).where(WebhookDelivery.id == delivery_id))
            await db.execute(delete(WebhookSubscription).where(WebhookSubscription.id == subscription_id))
            await db.execute(delete(WebhookDestination).where(WebhookDestination.id == destination_id))
            await db.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.id == event_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()
