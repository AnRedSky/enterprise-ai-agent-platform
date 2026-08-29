"""Phase 2.9-C Reliable Event Delivery 单元测试。"""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.integration import delivery
from app.services.integration.delivery import IntegrationEventDeliveryService


def test_retry_at_uses_capped_exponential_backoff() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0)
    assert IntegrationEventDeliveryService.retry_at(now, 1) == datetime(2026, 1, 1, 0, 0, 2)
    assert IntegrationEventDeliveryService.retry_at(now, 3) == datetime(2026, 1, 1, 0, 0, 8)
    assert IntegrationEventDeliveryService.retry_at(now, 20) == datetime(2026, 1, 1, 0, 5, 0)


def test_retry_at_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        IntegrationEventDeliveryService.retry_at(datetime.now(), 0)


class FakeSessionContext:
    """为 delivery service 单元测试提供无需 PostgreSQL 的 SessionLocal 替身。"""

    def __init__(self, session: MagicMock) -> None:
        self.session = session

    async def __aenter__(self) -> MagicMock:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _install_fake_sessions(monkeypatch: pytest.MonkeyPatch, *sessions: MagicMock) -> None:
    iterator = iter(sessions)
    monkeypatch.setattr(delivery, "SessionLocal", lambda: FakeSessionContext(next(iterator)))


@pytest.mark.asyncio
async def test_delivery_service_returns_false_when_no_event_is_claimable(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    repository = MagicMock()
    repository.claim_next = AsyncMock(return_value=None)
    _install_fake_sessions(monkeypatch, session)

    service = IntegrationEventDeliveryService(repository)
    sender = AsyncMock()

    assert await service.deliver_once(uuid.uuid4(), "worker-a", sender) is False
    repository.claim_next.assert_awaited_once()
    session.commit.assert_not_awaited()
    sender.assert_not_awaited()


@pytest.mark.asyncio
async def test_delivery_service_commits_claim_then_marks_delivered(monkeypatch: pytest.MonkeyPatch) -> None:
    claim_session = MagicMock()
    result_session = MagicMock()
    event_id = uuid.uuid4()
    record = SimpleNamespace(id=event_id, attempt_count=1, payload={"event": "ok"})
    repository = MagicMock()
    repository.claim_next = AsyncMock(return_value=record)
    repository.mark_delivered = AsyncMock(return_value=True)
    repository.mark_failed = AsyncMock()
    sender = AsyncMock()
    _install_fake_sessions(monkeypatch, claim_session, result_session)

    service = IntegrationEventDeliveryService(repository)
    tenant_id = uuid.uuid4()

    assert await service.deliver_once(tenant_id, "worker-a", sender) is True

    claim_session.commit.assert_awaited_once()
    sender.assert_awaited_once_with({"event": "ok"})
    repository.mark_delivered.assert_awaited_once()
    result_session.commit.assert_awaited_once()
    repository.mark_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_delivery_service_marks_retry_after_sender_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    claim_session = MagicMock()
    result_session = MagicMock()
    record = SimpleNamespace(id=uuid.uuid4(), attempt_count=1, payload={"event": "retry"})
    repository = MagicMock()
    repository.claim_next = AsyncMock(return_value=record)
    repository.mark_failed = AsyncMock(return_value=True)
    repository.mark_delivered = AsyncMock()
    sender = AsyncMock(side_effect=RuntimeError("temporary failure"))
    _install_fake_sessions(monkeypatch, claim_session, result_session)

    service = IntegrationEventDeliveryService(repository)

    assert await service.deliver_once(uuid.uuid4(), "worker-a", sender, max_attempts=5) is True

    sender.assert_awaited_once_with({"event": "retry"})
    repository.mark_failed.assert_awaited_once()
    failure_call = repository.mark_failed.await_args.args
    assert failure_call[1] == record.id
    assert failure_call[2] == "worker-a"
    assert failure_call[4] == "RuntimeError"
    assert failure_call[5] == "temporary failure"
    assert failure_call[6] is not None
    result_session.commit.assert_awaited_once()
    repository.mark_delivered.assert_not_awaited()
