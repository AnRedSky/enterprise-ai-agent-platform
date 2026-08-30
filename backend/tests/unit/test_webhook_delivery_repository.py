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
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _ScalarResult(self.record)


@pytest.mark.asyncio
async def test_claim_next_scopes_claim_to_tenant_and_consumer_group() -> None:
    """验证 Claim 查询同时包含 tenant 与 consumer group 隔离条件。"""
    tenant_id = uuid4()
    record = SimpleNamespace(
        id=uuid4(), tenant_id=tenant_id, integration_event_id=uuid4(), attempt_count=0,
        status="pending", lease_owner=None, lease_expires_at=None,
        last_error_code=None, last_error_message=None, response_status_code=None,
    )
    db = _FakeDb(record)
    now = datetime.now(UTC).replace(tzinfo=None)

    claimed = await WebhookDeliveryRepository().claim_next(
        db, now, "worker-a", tenant_id=tenant_id, consumer_group="phase-2.10-i",
    )

    assert claimed is record
    assert record.status == "running"
    assert record.attempt_count == 1
    assert db.statement is not None
    params = db.statement.compile().params
    assert params["tenant_id_1"] == tenant_id
    assert "phase-2.10-i" in params.values()


@pytest.mark.asyncio
async def test_claim_next_rejects_invalid_consumer_group() -> None:
    """验证 Worker Claim 不允许空或超长 consumer group。"""
    db = _FakeDb(None)
    now = datetime.now(UTC).replace(tzinfo=None)

    with pytest.raises(ValueError, match="consumer_group"):
        await WebhookDeliveryRepository().claim_next(db, now, "worker-a", consumer_group="   ")


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
    assert db.add.call_count == 1


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
