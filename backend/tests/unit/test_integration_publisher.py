from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.integration.publisher import RuntimeIntegrationEventPublisher


class _NestedTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_publish_normalizes_naive_occurred_at_as_utc(monkeypatch):
    db = MagicMock()
    db.begin_nested.return_value = _NestedTransaction()
    publisher = RuntimeIntegrationEventPublisher(db)
    record = object()
    publisher.repository.create = AsyncMock(return_value=record)

    occurred_at = datetime(2026, 8, 30, 9, 30, 0)
    result = await publisher.publish(
        tenant_id=uuid4(),
        event_type="alert.firing",
        source="alert_lifecycle",
        subject=str(uuid4()),
        idempotency_key="test-naive-time",
        payload={"value": 1},
        occurred_at=occurred_at,
    )

    assert result is record
    event = publisher.repository.create.await_args.args[1]
    assert event.occurred_at == occurred_at.replace(tzinfo=UTC)


@pytest.mark.asyncio
async def test_publish_normalizes_aware_occurred_at_to_utc():
    db = MagicMock()
    db.begin_nested.return_value = _NestedTransaction()
    publisher = RuntimeIntegrationEventPublisher(db)
    publisher.repository.create = AsyncMock(return_value=object())

    offset = timezone = UTC
    occurred_at = datetime(2026, 8, 30, 17, 30, tzinfo=offset)
    await publisher.publish(
        tenant_id=uuid4(),
        event_type="alert.recovery",
        source="alert_lifecycle",
        subject=str(uuid4()),
        idempotency_key="test-aware-time",
        payload={"value": 0},
        occurred_at=occurred_at + timedelta(hours=1),
    )

    event = publisher.repository.create.await_args.args[1]
    assert event.occurred_at.tzinfo == UTC
    assert event.occurred_at == occurred_at + timedelta(hours=1)
