from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow.frontier_repository import claim_next_frontier, recover_expired_frontiers, release_frontier_lease, transition_owned_frontier


@pytest.mark.asyncio
async def test_claim_next_frontier_uses_locked_schedulable_query_without_commit() -> None:
    db = MagicMock(); frontier = MagicMock(); execution_id = uuid4(); tenant_id = uuid4()
    candidate = MagicMock(); candidate.scalar_one_or_none.return_value = frontier.id
    identity = MagicMock(); identity.one_or_none.return_value = (execution_id, tenant_id)
    execution = MagicMock(); execution.status = "pending"; execution.worker_owner = None; execution.worker_lease_expires_at = None
    execution_result = MagicMock(); execution_result.scalar_one_or_none.return_value = execution
    frontier_result = MagicMock(); frontier_result.scalar_one_or_none.return_value = frontier
    overlap_result = MagicMock(); overlap_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[candidate, identity, execution_result, frontier_result, overlap_result])
    db.flush = AsyncMock(); db.commit = AsyncMock()
    now = datetime(2026, 8, 27, 8, 0, 0)
    claimed = await claim_next_frontier(db, tenant_id=tenant_id, worker_owner="worker-a", lease_expires_at=now + timedelta(minutes=5), now=now)
    assert claimed is frontier
    assert frontier.status == "claimed"; assert frontier.worker_owner == "worker-a"; assert frontier.attempt == 1
    db.flush.assert_awaited_once(); db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_claim_next_frontier_returns_none_when_queue_is_empty() -> None:
    db = MagicMock(); result = MagicMock(); result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result); db.flush = AsyncMock(); db.commit = AsyncMock()
    now = datetime(2026, 8, 27, 8, 0, 0)
    assert await claim_next_frontier(db, tenant_id=uuid4(), worker_owner="worker-a", lease_expires_at=now + timedelta(minutes=5), now=now) is None
    db.flush.assert_not_awaited(); db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_recover_expired_frontiers_returns_expired_work_to_retry_queue() -> None:
    db = MagicMock(); frontier = MagicMock(); frontier.status = "running"; frontier.worker_owner = "worker-a"; frontier.worker_lease_expires_at = datetime(2026, 8, 27, 7, 59)
    result = MagicMock(); result.scalars.return_value.all.return_value = [frontier]
    db.execute = AsyncMock(return_value=result); db.flush = AsyncMock(); db.commit = AsyncMock()
    now = datetime(2026, 8, 27, 8, 0)
    recovered = await recover_expired_frontiers(db, now=now)
    assert recovered == [frontier]; assert frontier.status == "retry_wait"; assert frontier.worker_owner is None; assert frontier.worker_lease_expires_at is None; assert frontier.available_at == now; assert frontier.error_code == "FRONTIER_LEASE_EXPIRED"
    db.flush.assert_awaited_once(); db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_recover_expired_frontiers_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError, match="limit must be positive"):
        await recover_expired_frontiers(AsyncMock(), now=datetime(2026, 8, 27, 8, 0), limit=0)


@pytest.mark.asyncio
async def test_transition_owned_frontier_uses_owner_and_attempt_as_fencing_generation() -> None:
    db = MagicMock(); frontier = MagicMock(); frontier.id = uuid4(); result = MagicMock(); result.scalar_one_or_none.return_value = frontier
    db.execute = AsyncMock(return_value=result); db.flush = AsyncMock(); db.commit = AsyncMock(); now = datetime(2026, 8, 27, 8, 0)
    updated = await transition_owned_frontier(db, frontier_id=frontier.id, worker_owner="worker-a", attempt=3, target_status="completed", now=now)
    assert updated is frontier; assert frontier.status == "completed"; assert frontier.completed_at == now; assert frontier.worker_owner is None; assert frontier.worker_lease_expires_at is None
    db.flush.assert_awaited_once(); db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_transition_owned_frontier_rejects_stale_worker() -> None:
    db = MagicMock(); result = MagicMock(); result.scalar_one_or_none.return_value = None; db.execute = AsyncMock(return_value=result); db.flush = AsyncMock(); db.commit = AsyncMock()
    with pytest.raises(ValueError, match="ownership or fencing generation mismatch"):
        await transition_owned_frontier(db, frontier_id=uuid4(), worker_owner="worker-a", attempt=2, target_status="completed", now=datetime(2026, 8, 27, 8, 0))
    db.flush.assert_not_awaited(); db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_release_frontier_lease_requires_current_owner() -> None:
    db = MagicMock(); frontier = MagicMock(); frontier.worker_owner = "worker-a"; db.flush = AsyncMock(); db.commit = AsyncMock()
    await release_frontier_lease(db, frontier=frontier, worker_owner="worker-a")
    assert frontier.worker_owner is None; assert frontier.worker_lease_expires_at is None; db.flush.assert_awaited_once(); db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_release_frontier_lease_rejects_stale_worker() -> None:
    db = MagicMock(); frontier = MagicMock(); frontier.worker_owner = "worker-b"; db.flush = AsyncMock(); db.commit = AsyncMock()
    with pytest.raises(ValueError, match="ownership mismatch"):
        await release_frontier_lease(db, frontier=frontier, worker_owner="worker-a")
    db.flush.assert_not_awaited(); db.commit.assert_not_awaited()
