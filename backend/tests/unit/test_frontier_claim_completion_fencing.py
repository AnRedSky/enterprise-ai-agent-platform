"""Durable Frontier Claim / Completion ownership 交叉回归测试。

职责：补充 Claim 后 Execution lease 丢失时的 stale Worker completion fencing。
边界：只验证既有 Claim / Progression Contract，不复制生产 ownership 算法。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.workflow.frontier_progression import (
    FrontierProgressionContractError,
    complete_frontier_with_checkpoint,
)


def _frontier() -> MagicMock:
    frontier = MagicMock()
    frontier.id = uuid4()
    frontier.execution_id = uuid4()
    frontier.workflow_version_id = uuid4()
    frontier.tenant_id = uuid4()
    frontier.frontier_key = "stale-worker-frontier"
    frontier.attempt = 3
    return frontier


def _execution(frontier: MagicMock) -> MagicMock:
    execution = MagicMock()
    execution.id = frontier.execution_id
    execution.status = "running"
    execution.worker_owner = "worker-b"
    execution.worker_lease_expires_at = datetime(2026, 8, 27, 8, 10)
    execution.worker_attempt = 8
    execution.created_by = uuid4()
    return execution


def _lookup(value: MagicMock | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_stale_worker_completion_rejects_changed_execution_owner() -> None:
    """Claim 后 Execution ownership 已切换时，旧 Worker 不得写入 completion fact。"""
    db = AsyncMock()
    frontier = _frontier()
    execution = _execution(frontier)
    db.execute.side_effect = [_lookup(None), _lookup(execution)]

    with patch(
        "app.services.workflow.frontier_progression.transition_owned_frontier",
        new_callable=AsyncMock,
    ) as transition:
        with pytest.raises(FrontierProgressionContractError, match="Worker ownership 已失效"):
            await complete_frontier_with_checkpoint(
                db,
                frontier=frontier,
                worker_owner="worker-a",
                attempt=3,
                checkpoint_state={"done": True},
                checkpoint_reason="frontier_completed",
                next_identity=None,
                now=datetime(2026, 8, 27, 8, 0),
            )

    transition.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_worker_completion_rejects_expired_execution_lease() -> None:
    """旧 Worker 即使仍保留 owner 字段，也不得在 Execution lease 过期后 completion。"""
    db = AsyncMock()
    frontier = _frontier()
    execution = _execution(frontier)
    execution.worker_owner = "worker-a"
    execution.worker_lease_expires_at = datetime(2026, 8, 27, 7, 59)
    db.execute.side_effect = [_lookup(None), _lookup(execution)]

    with pytest.raises(FrontierProgressionContractError, match="Worker lease 已失效"):
        await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=3,
            checkpoint_state={"done": True},
            checkpoint_reason="frontier_completed",
            next_identity=None,
            now=datetime(2026, 8, 27, 8, 0),
        )

    db.commit.assert_not_awaited()
