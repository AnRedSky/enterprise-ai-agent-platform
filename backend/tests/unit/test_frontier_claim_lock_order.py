"""Frontier Claim / Completion 锁序回归测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow.frontier_repository import claim_next_frontier


def _result(*, scalar=None, one=None, scalars=None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    result.one_or_none.return_value = one
    result.scalars.return_value.all.return_value = [] if scalars is None else scalars
    return result


@pytest.mark.asyncio
async def test_claim_locks_execution_before_frontier() -> None:
    """Claim 必须先锁 Execution，再锁候选 Frontier，避免与 completion 形成反向锁序。"""
    db = AsyncMock()
    tenant_id = uuid4()
    execution_id = uuid4()
    frontier_id = uuid4()
    now = datetime(2026, 8, 27, 8, 0)

    execution = MagicMock()
    execution.id = execution_id
    execution.tenant_id = tenant_id
    execution.status = "pending"
    execution.worker_owner = None
    execution.worker_lease_expires_at = None

    frontier = MagicMock()
    frontier.id = frontier_id
    frontier.tenant_id = tenant_id
    frontier.execution_id = execution_id
    frontier.status = "pending"
    frontier.available_at = now
    frontier.node_ids = ["node-a"]
    frontier.attempt = 0

    db.execute.side_effect = [
        _result(scalar=frontier_id),
        _result(one=(execution_id, tenant_id)),
        _result(scalar=execution),
        _result(scalar=frontier),
        _result(scalars=[]),
    ]

    claimed = await claim_next_frontier(
        db,
        tenant_id=tenant_id,
        worker_owner="worker-a",
        lease_expires_at=datetime(2026, 8, 27, 8, 5),
        now=now,
    )

    assert claimed is frontier
    assert frontier.status == "claimed"
    assert frontier.worker_owner == "worker-a"
    assert frontier.attempt == 1

    statements = [call.args[0] for call in db.execute.await_args_list]
    candidate_lock = getattr(statements[0], "_for_update_arg", None)
    execution_lock = getattr(statements[2], "_for_update_arg", None)
    frontier_lock = getattr(statements[3], "_for_update_arg", None)

    assert candidate_lock is None
    assert execution_lock is not None
    assert execution_lock.skip_locked is True
    assert frontier_lock is not None
    assert frontier_lock.skip_locked is True


@pytest.mark.asyncio
async def test_claim_returns_none_when_execution_is_locked() -> None:
    """Execution 被其他 progression 锁住时，Claim 必须 fail-closed，不能先持有 Frontier 锁。"""
    db = AsyncMock()
    tenant_id = uuid4()
    execution_id = uuid4()
    frontier_id = uuid4()
    now = datetime(2026, 8, 27, 8, 0)

    db.execute.side_effect = [
        _result(scalar=frontier_id),
        _result(one=(execution_id, tenant_id)),
        _result(scalar=None),
    ]

    result = await claim_next_frontier(
        db,
        tenant_id=tenant_id,
        worker_owner="worker-a",
        lease_expires_at=datetime(2026, 8, 27, 8, 5),
        now=now,
    )

    assert result is None
    assert db.execute.await_count == 3
    db.flush.assert_not_awaited()
