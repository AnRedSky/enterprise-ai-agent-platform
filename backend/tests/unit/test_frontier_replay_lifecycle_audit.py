"""Durable Frontier Replay lifecycle convergence audit tests."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
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
    frontier.frontier_key = "frontier-current"
    frontier.attempt = 2
    frontier.status = "completed"
    frontier.node_ids = ["node-a"]
    return frontier


@pytest.mark.asyncio
async def test_replay_does_not_bind_to_ephemeral_worker_owner() -> None:
    """Replay 可由新的 Worker 收敛，不能把 ephemeral worker owner 当作 Durable identity。"""
    db = AsyncMock()
    frontier = _frontier()
    current_lookup = MagicMock()
    current_lookup.scalar_one_or_none.return_value = frontier
    checkpoint_lookup = MagicMock()
    checkpoint = MagicMock()
    checkpoint.state_data = {"done": True}
    checkpoint.worker_owner = "worker-old"
    checkpoint.execution_status = "completed"
    checkpoint_lookup.scalars.return_value.all.return_value = [checkpoint]
    execution_lookup = MagicMock()
    execution = MagicMock()
    execution.status = "completed"
    execution_lookup.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [current_lookup, checkpoint_lookup, execution_lookup]

    result = await complete_frontier_with_checkpoint(
        db, frontier=frontier, worker_owner="worker-new", attempt=2,
        checkpoint_state={"done": True}, checkpoint_reason="frontier_completed",
        next_identity=None, now=datetime(2026, 8, 27, 8, 0),
    )

    assert result == (checkpoint, None)


@pytest.mark.asyncio
async def test_replay_rejects_checkpoint_execution_lifecycle_drift() -> None:
    """Checkpoint 与当前 Execution lifecycle 分叉时必须 fail-closed。"""
    db = AsyncMock()
    frontier = _frontier()
    current_lookup = MagicMock()
    current_lookup.scalar_one_or_none.return_value = frontier
    checkpoint_lookup = MagicMock()
    checkpoint = MagicMock()
    checkpoint.state_data = {"done": True}
    checkpoint.worker_owner = "worker-old"
    checkpoint.execution_status = "running"
    checkpoint_lookup.scalars.return_value.all.return_value = [checkpoint]
    execution_lookup = MagicMock()
    execution = MagicMock()
    execution.status = "completed"
    execution_lookup.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [current_lookup, checkpoint_lookup, execution_lookup]

    with pytest.raises(FrontierProgressionContractError, match="lifecycle 不一致"):
        await complete_frontier_with_checkpoint(
            db, frontier=frontier, worker_owner="worker-new", attempt=2,
            checkpoint_state={"done": True}, checkpoint_reason="frontier_completed",
            next_identity=None, now=datetime(2026, 8, 27, 8, 0),
        )
