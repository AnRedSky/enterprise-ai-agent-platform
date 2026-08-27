"""Durable Frontier duplicate completion 的单元测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.workflow.frontier import WorkflowFrontierIdentity
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
    frontier.frontier_key = "current-key"
    return frontier


def _completed_frontier_result(frontier: MagicMock) -> MagicMock:
    current = MagicMock()
    current.id = frontier.id
    current.execution_id = frontier.execution_id
    current.workflow_version_id = frontier.workflow_version_id
    current.tenant_id = frontier.tenant_id
    current.status = "completed"
    return current


@pytest.mark.asyncio
async def test_duplicate_terminal_completion_returns_existing_checkpoint_without_transition() -> None:
    db = AsyncMock()
    frontier = _frontier()
    existing_frontier = _completed_frontier_result(frontier)
    checkpoint = MagicMock()
    checkpoint.state_data = {"done": True}
    checkpoint.worker_owner = "worker-a"

    frontier_result = MagicMock()
    frontier_result.scalar_one_or_none.return_value = existing_frontier
    checkpoint_result = MagicMock()
    checkpoint_result.scalar_one_or_none.return_value = checkpoint
    db.execute.side_effect = [frontier_result, checkpoint_result]

    with patch(
        "app.services.workflow.frontier_progression.transition_owned_frontier",
        new_callable=AsyncMock,
    ) as transition:
        result = await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=4,
            checkpoint_state={"done": True},
            checkpoint_reason="frontier_completed",
            next_identity=None,
            now=datetime(2026, 8, 27, 8, 0),
        )

    assert result == (checkpoint, None)
    transition.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_completion_rejects_payload_drift() -> None:
    db = AsyncMock()
    frontier = _frontier()
    existing_frontier = _completed_frontier_result(frontier)
    checkpoint = MagicMock()
    checkpoint.state_data = {"done": True}
    checkpoint.worker_owner = "worker-a"

    frontier_result = MagicMock()
    frontier_result.scalar_one_or_none.return_value = existing_frontier
    checkpoint_result = MagicMock()
    checkpoint_result.scalar_one_or_none.return_value = checkpoint
    db.execute.side_effect = [frontier_result, checkpoint_result]

    with pytest.raises(FrontierProgressionContractError, match="payload 与既有 Durable fact 不一致"):
        await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=4,
            checkpoint_state={"done": False},
            checkpoint_reason="frontier_completed",
            next_identity=None,
            now=datetime(2026, 8, 27, 8, 0),
        )


@pytest.mark.asyncio
async def test_duplicate_non_terminal_completion_requires_existing_next_frontier() -> None:
    db = AsyncMock()
    frontier = _frontier()
    existing_frontier = _completed_frontier_result(frontier)
    checkpoint = MagicMock()
    checkpoint.state_data = {"branch": "A"}
    checkpoint.worker_owner = "worker-a"
    next_identity = WorkflowFrontierIdentity(
        execution_id=frontier.execution_id,
        workflow_version_id=frontier.workflow_version_id,
        decision_fingerprint="next",
        node_ids=("node-b", "node-c"),
    )

    frontier_result = MagicMock()
    frontier_result.scalar_one_or_none.return_value = existing_frontier
    checkpoint_result = MagicMock()
    checkpoint_result.scalar_one_or_none.return_value = checkpoint
    next_result = MagicMock()
    next_result.scalar_one_or_none.return_value = MagicMock(
        execution_id=frontier.execution_id,
        workflow_version_id=frontier.workflow_version_id,
    )
    db.execute.side_effect = [frontier_result, checkpoint_result, next_result]

    with patch(
        "app.services.workflow.frontier_progression.transition_owned_frontier",
        new_callable=AsyncMock,
    ) as transition:
        result = await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=4,
            checkpoint_state={"branch": "A"},
            checkpoint_reason="frontier_completed",
            next_identity=next_identity,
            now=datetime(2026, 8, 27, 8, 0),
        )

    assert result[0] is checkpoint
    assert result[1] is not None
    transition.assert_not_awaited()
