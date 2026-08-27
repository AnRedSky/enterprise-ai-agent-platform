"""Durable Frontier progression 锁序约束的单元测试。

验证 Next Frontier sibling overlap 检查只读取 sibling Frontier，不再次取得行锁，避免在已持有
Execution 锁后形成 Execution → sibling Frontier 的反向锁序。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow.frontier_progression import (
    FrontierProgressionContractError,
    _assert_next_frontier_has_no_active_node_overlap,
)


@pytest.mark.asyncio
async def test_next_frontier_overlap_audit_does_not_lock_sibling_frontiers() -> None:
    """已持有 Execution 锁时，sibling overlap 查询不得再取得 Frontier 行锁。"""
    db = AsyncMock()
    frontier = MagicMock()
    frontier.id = uuid4()
    frontier.tenant_id = uuid4()
    frontier.execution_id = uuid4()

    active = MagicMock()
    active.node_ids = ["node-b"]
    lookup = MagicMock()
    lookup.scalars.return_value.all.return_value = [active]
    db.execute.return_value = lookup

    next_identity = MagicMock()
    next_identity.node_ids = ("node-a", "node-b")

    with pytest.raises(FrontierProgressionContractError, match="Node 重叠"):
        await _assert_next_frontier_has_no_active_node_overlap(
            db, frontier=frontier, next_identity=next_identity,
        )

    statement = db.execute.await_args.args[0]
    assert statement._for_update_arg is None


@pytest.mark.asyncio
async def test_next_frontier_disjoint_overlap_audit_keeps_sibling_query_unlocked() -> None:
    """无 Node 重叠时 sibling 查询继续保持普通一致性读取，不引入反向锁。"""
    db = AsyncMock()
    frontier = MagicMock()
    frontier.id = uuid4()
    frontier.tenant_id = uuid4()
    frontier.execution_id = uuid4()

    active = MagicMock()
    active.node_ids = ["node-c"]
    lookup = MagicMock()
    lookup.scalars.return_value.all.return_value = [active]
    db.execute.return_value = lookup

    next_identity = MagicMock()
    next_identity.node_ids = ("node-a", "node-b")

    await _assert_next_frontier_has_no_active_node_overlap(
        db, frontier=frontier, next_identity=next_identity,
    )

    statement = db.execute.await_args.args[0]
    assert statement._for_update_arg is None
