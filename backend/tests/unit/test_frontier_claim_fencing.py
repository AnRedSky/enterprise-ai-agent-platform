"""Durable Frontier Claim 层并行消费 fencing 的单元测试。

验证同一 Execution 的活动 Frontier Node 集合在 Claim 事务内保持互斥，并验证不同 Execution/Node 集合
仍可正常进入 claimed 状态。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow.frontier_repository import claim_next_frontier


def _frontier(*, execution_id=None, node_ids=None) -> MagicMock:
    frontier = MagicMock()
    frontier.id = uuid4()
    frontier.execution_id = execution_id or uuid4()
    frontier.tenant_id = uuid4()
    frontier.status = "pending"
    frontier.available_at = datetime(2026, 8, 27, 8, 0)
    frontier.node_ids = node_ids or ["node-a"]
    frontier.attempt = 0
    return frontier


def _execution(frontier: MagicMock, *, owner: str = "worker-a") -> MagicMock:
    execution = MagicMock()
    execution.id = frontier.execution_id
    execution.tenant_id = frontier.tenant_id
    execution.status = "running"
    execution.worker_owner = owner
    execution.worker_lease_expires_at = datetime(2026, 8, 27, 9, 0)
    execution.worker_attempt = 3
    return execution


def _lookup(value) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _identity_lookup(execution_id, tenant_id) -> MagicMock:
    result = MagicMock()
    result.one_or_none.return_value = (execution_id, tenant_id)
    return result


def _active_lookup(frontiers: list[MagicMock]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = frontiers
    return result


@pytest.mark.asyncio
async def test_claim_rejects_overlap_with_active_frontier() -> None:
    db = AsyncMock()
    execution_id = uuid4()
    candidate = _frontier(execution_id=execution_id, node_ids=["node-a", "node-b"])
    execution = _execution(candidate)
    active = _frontier(execution_id=execution_id, node_ids=["node-b", "node-c"])
    db.execute.side_effect = [
        _lookup(candidate.id),
        _identity_lookup(candidate.execution_id, candidate.tenant_id),
        _lookup(execution),
        _lookup(candidate),
        _active_lookup([active]),
    ]

    result = await claim_next_frontier(
        db,
        tenant_id=candidate.tenant_id,
        worker_owner="worker-a",
        lease_expires_at=datetime(2026, 8, 27, 9, 0),
        now=datetime(2026, 8, 27, 8, 0),
    )

    assert result is None
    assert candidate.status == "pending"
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_claim_allows_disjoint_frontier_in_same_execution() -> None:
    db = AsyncMock()
    execution_id = uuid4()
    candidate = _frontier(execution_id=execution_id, node_ids=["node-a", "node-b"])
    execution = _execution(candidate)
    active = _frontier(execution_id=execution_id, node_ids=["node-c", "node-d"])
    db.execute.side_effect = [
        _lookup(candidate.id),
        _identity_lookup(candidate.execution_id, candidate.tenant_id),
        _lookup(execution),
        _lookup(candidate),
        _active_lookup([active]),
    ]

    result = await claim_next_frontier(
        db,
        tenant_id=candidate.tenant_id,
        worker_owner="worker-a",
        lease_expires_at=datetime(2026, 8, 27, 9, 0),
        now=datetime(2026, 8, 27, 8, 0),
    )

    assert result is candidate
    assert candidate.status == "claimed"
    assert candidate.worker_owner == "worker-a"
    assert candidate.worker_lease_expires_at == datetime(2026, 8, 27, 9, 0)
    assert candidate.attempt == 1
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_claim_does_not_consume_when_execution_lock_is_unavailable() -> None:
    db = AsyncMock()
    candidate = _frontier()
    db.execute.side_effect = [
        _lookup(candidate.id),
        _identity_lookup(candidate.execution_id, candidate.tenant_id),
        _lookup(None),
    ]

    result = await claim_next_frontier(
        db,
        tenant_id=candidate.tenant_id,
        worker_owner="worker-a",
        lease_expires_at=datetime(2026, 8, 27, 9, 0),
        now=datetime(2026, 8, 27, 8, 0),
    )

    assert result is None
    assert candidate.status == "pending"
    db.flush.assert_not_awaited()
