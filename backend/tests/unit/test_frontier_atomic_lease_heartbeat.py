"""Unit tests for atomic Durable Frontier / Execution lease heartbeat."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.frontier_lease_repository import renew_owned_frontier_lease


class _Result:
    def __init__(self, rowcount: int = 1, execution_id=None):
        self.rowcount = rowcount
        self._execution_id = execution_id

    def scalar_one_or_none(self):
        return self._execution_id


@pytest.mark.asyncio
async def test_heartbeat_renews_frontier_and_execution_in_same_transaction(monkeypatch):
    frontier_id = uuid4()
    execution_id = uuid4()
    db = SimpleNamespace()
    db.execute = AsyncMock(side_effect=[_Result(1), _Result(1, execution_id), _Result(1)])
    db.flush = AsyncMock()
    db.rollback = AsyncMock()

    # Repository uses SQLAlchemy expressions; this test focuses on the durable
    # transaction contract and verifies both UPDATEs plus the final flush.
    result = await renew_owned_frontier_lease(
        db,
        frontier_id=frontier_id,
        worker_owner="worker:test",
        attempt=3,
        lease_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=60),
        now=datetime.now(UTC).replace(tzinfo=None),
    )

    assert result is True
    assert db.execute.await_count == 3
    db.flush.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_heartbeat_rolls_back_when_execution_lease_cannot_be_renewed(monkeypatch):
    frontier_id = uuid4()
    execution_id = uuid4()
    db = SimpleNamespace()
    db.execute = AsyncMock(side_effect=[_Result(1), _Result(1, execution_id), _Result(0)])
    db.flush = AsyncMock()
    db.rollback = AsyncMock()

    result = await renew_owned_frontier_lease(
        db,
        frontier_id=frontier_id,
        worker_owner="worker:test",
        attempt=3,
        lease_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=60),
        now=datetime.now(UTC).replace(tzinfo=None),
    )

    assert result is False
    db.rollback.assert_awaited_once()
    db.flush.assert_not_awaited()
