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


def _execution(frontier: MagicMock, *, status: str) -> MagicMock:
    execution = MagicMock()
    execution.id = frontier.execution_id
    execution.status = status
    execution.worker_owner = "worker-a"
    execution.worker_lease_expires_at = datetime(2026, 8, 27, 9, 0)
    execution.worker_attempt = 7
    execution.created_by = uuid4()
    return execution


def _checkpoint(state_data: dict, *, execution_status: str) -> MagicMock:
    checkpoint = MagicMock()
    checkpoint.state_data = state_data
    checkpoint.worker_owner = "worker-a"
    checkpoint.execution_status = execution_status
    return checkpoint


def _checkpoint_lookup(checkpoint: MagicMock) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = [checkpoint]
    return result


@pytest.mark.asyncio
async def test_duplicate_terminal_completion_returns_existing_checkpoint_without_transition() -> None:
    db = AsyncMock()
    frontier = _frontier()
    existing_frontier = _completed_frontier_result(frontier)
    checkpoint = _checkpoint({"done": True}, execution_status="completed")
    execution = _execution(frontier, status="completed")

    frontier_result = MagicMock()
    frontier_result.scalar_one_or_none.return_value = existing_frontier
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [frontier_result, _checkpoint_lookup(checkpoint), execution_result]

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
    checkpoint = _checkpoint({"done": True}, execution_status="completed")
    execution = _execution(frontier, status="completed")

    frontier_result = MagicMock()
    frontier_result.scalar_one_or_none.return_value = existing_frontier
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [frontier_result, _checkpoint_lookup(checkpoint), execution_result]

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
    checkpoint = _checkpoint({"branch": "A"}, execution_status="running")
    execution = _execution(frontier, status="running")
    next_identity = WorkflowFrontierIdentity(
        execution_id=frontier.execution_id,
        workflow_version_id=frontier.workflow_version_id,
        decision_fingerprint="next",
        node_ids=("node-b", "node-c"),
    )

    existing_next = MagicMock(
        execution_id=frontier.execution_id,
        workflow_version_id=frontier.workflow_version_id,
        decision_fingerprint="next",
        node_ids=["node-b", "node-c"],
    )
    frontier_result = MagicMock()
    frontier_result.scalar_one_or_none.return_value = existing_frontier
    next_result = MagicMock()
    next_result.scalar_one_or_none.return_value = existing_next
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [frontier_result, _checkpoint_lookup(checkpoint), execution_result, next_result]

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

    assert result == (checkpoint, existing_next)
    transition.assert_not_awaited()
