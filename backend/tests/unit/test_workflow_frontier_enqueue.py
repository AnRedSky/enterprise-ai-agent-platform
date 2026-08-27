"""Durable Frontier 入队边界单元测试。

职责：验证 Frontier 幂等入队只负责数据库写入与 flush，不复制 Scheduler/Planner 规则。
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_repository import enqueue_frontier


@pytest.mark.asyncio
async def test_enqueue_frontier_uses_deterministic_identity_and_does_not_commit() -> None:
    """相同 Frontier identity 使用同一幂等键，并且仓储不提交外层事务。"""
    db = MagicMock()
    execute_result = MagicMock()
    frontier_id = uuid4()
    execute_result.scalar_one_or_none.side_effect = [frontier_id]
    db.execute = AsyncMock(return_value=execute_result)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db_frontier_result = MagicMock()
    db_frontier_result.scalar_one.return_value = MagicMock(id=frontier_id)
    db.execute.side_effect = [execute_result, db_frontier_result]

    identity = WorkflowFrontierIdentity(
        execution_id=uuid4(),
        workflow_version_id=uuid4(),
        decision_fingerprint="initial",
        node_ids=("root-a", "root-b"),
    )
    result = await enqueue_frontier(
        db,
        tenant_id=uuid4(),
        identity=identity,
        node_ids=identity.node_ids,
        now=MagicMock(),
    )

    assert result.id == frontier_id
    db.flush.assert_awaited_once()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_enqueue_frontier_returns_existing_row_after_unique_conflict() -> None:
    """并发唯一键冲突时读取已经存在的 Frontier，而不是创建第二个 work item。"""
    db = MagicMock()
    insert_result = MagicMock()
    insert_result.scalar_one_or_none.return_value = None
    existing = MagicMock(id=uuid4())
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(side_effect=[insert_result, select_result])

    identity = WorkflowFrontierIdentity(
        execution_id=uuid4(),
        workflow_version_id=uuid4(),
        decision_fingerprint="initial",
        node_ids=("root",),
    )
    result = await enqueue_frontier(
        db,
        tenant_id=uuid4(),
        identity=identity,
        node_ids=identity.node_ids,
        now=MagicMock(),
    )

    assert result is existing
    db.commit = AsyncMock()
    db.commit.assert_not_called()
