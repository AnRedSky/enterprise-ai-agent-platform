"""Durable Frontier terminal Replay lifecycle boundary 单元测试。"""

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
    frontier.attempt = 1
    return frontier


def _checkpoint(execution_status: str) -> MagicMock:
    checkpoint = MagicMock()
    checkpoint.state_data = {"done": True}
    checkpoint.worker_owner = "worker-a"
    checkpoint.execution_status = execution_status
    return checkpoint


def _checkpoint_result(execution_status: str) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = [_checkpoint(execution_status)]
    return result


@pytest.mark.asyncio
async def test_running_completion_replay_requires_next_frontier_identity() -> None:
    db = AsyncMock()
    frontier = _frontier()
    current_lookup = MagicMock()
    current_lookup.scalar_one_or_none.return_value = frontier
    execution = MagicMock()
    execution.status = "running"
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [current_lookup, _checkpoint_result("running"), execution_result]

    with pytest.raises(FrontierProgressionContractError, match="Replay 必须提供原始 Next Frontier identity"):
        await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=1,
            checkpoint_state={"done": True},
            checkpoint_reason="frontier_completed",
            next_identity=None,
            now=datetime(2026, 8, 27, 8, 0),
        )


@pytest.mark.asyncio
async def test_completed_terminal_replay_rejects_next_frontier_identity() -> None:
    db = AsyncMock()
    frontier = _frontier()
    current_lookup = MagicMock()
    current_lookup.scalar_one_or_none.return_value = frontier
    execution = MagicMock()
    execution.status = "completed"
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [current_lookup, _checkpoint_result("completed"), execution_result]

    next_identity = MagicMock()
    next_identity.key.return_value = "frontier-next"
    next_identity.execution_id = frontier.execution_id
    next_identity.workflow_version_id = frontier.workflow_version_id
    next_identity.decision_fingerprint = "fingerprint"
    next_identity.node_ids = ("node-next",)

    with pytest.raises(FrontierProgressionContractError, match="不得追加 Next Frontier identity"):
        await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=1,
            checkpoint_state={"done": True},
            checkpoint_reason="frontier_completed",
            next_identity=next_identity,
            now=datetime(2026, 8, 27, 8, 0),
        )
