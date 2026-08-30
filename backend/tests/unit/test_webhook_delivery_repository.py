from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.services.integration.webhook_delivery_repository import WebhookDeliveryRepository


class _ScalarResult:
    def __init__(self, record):
        self._record = record

    def scalar_one_or_none(self):
        return self._record


class _FakeDb:
    def __init__(self, record):
        self.record = record
        self.add = Mock()
        self.flush = AsyncMock()

    async def execute(self, _statement):
        return _ScalarResult(self.record)


@pytest.mark.asyncio
async def test_mark_failed_dead_letters_when_persisted_attempt_count_exhausts_max_attempts() -> None:
    """验证即使 Worker 传入可重试时间，持久化尝试次数耗尽仍必须进入死信。"""
    delivery_id = uuid4()
    record = SimpleNamespace(
        id=delivery_id,
        tenant_id=uuid4(),
        integration_event_id=uuid4(),
        attempt_count=1,
        status="running",
        lease_owner="worker-a",
        lease_expires_at=datetime.now(UTC).replace(tzinfo=None),
        last_error_code=None,
        last_error_message=None,
        response_status_code=None,
        next_attempt_at=None,
    )
    db = _FakeDb(record)

    updated = await WebhookDeliveryRepository().mark_failed(
        db,
        delivery_id,
        "worker-a",
        datetime.now(UTC).replace(tzinfo=None),
        "RuntimeError",
        "primary provider failure",
        datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=2),
        max_attempts=1,
    )

    assert updated is True
    assert record.status == "dead_letter"
    assert record.next_attempt_at is None
    assert record.lease_owner is None
    assert record.lease_expires_at is None
    db.flush.assert_awaited()
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_mark_failed_keeps_pending_before_max_attempts() -> None:
    """验证尚未耗尽尝试次数时仍保留 retry 时间并进入 pending。"""
    delivery_id = uuid4()
    retry_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=2)
    record = SimpleNamespace(
        id=delivery_id,
        tenant_id=uuid4(),
        integration_event_id=uuid4(),
        attempt_count=1,
        status="running",
        lease_owner="worker-a",
        lease_expires_at=datetime.now(UTC).replace(tzinfo=None),
        last_error_code=None,
        last_error_message=None,
        response_status_code=None,
        next_attempt_at=None,
    )
    db = _FakeDb(record)

    updated = await WebhookDeliveryRepository().mark_failed(
        db,
        delivery_id,
        "worker-a",
        datetime.now(UTC).replace(tzinfo=None),
        "RuntimeError",
        "temporary provider failure",
        retry_at,
        max_attempts=3,
    )

    assert updated is True
    assert record.status == "pending"
    assert record.next_attempt_at == retry_at
    assert record.lease_owner is None
    assert record.lease_expires_at is None
