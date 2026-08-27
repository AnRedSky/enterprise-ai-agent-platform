"""Durable Frontier 并行消费去重的单元测试。

验证同一 Execution 的 Next Frontier 不会与其他活动 Frontier 重叠消费同一个 Node。
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
    frontier.frontier_key = "frontier-current"
    frontier.attempt = 2
    return frontier


def _execution(frontier: MagicMock) -> MagicMock:
    execution = MagicMock()
    execution.id = frontier.execution_id
    execution.status = "running"
    execution.worker_owner = "worker-a"
    execution.worker_lease_expires_at = datetime(2026, 8, 27, 9, 0)
    execution.worker_attempt = 7
    execution.created_by = uuid4()
    return execution


@pytest.mark.asyncio
async def test_next_frontier_rejects_node_overlap_with_active_frontier() -> None:
    db = AsyncMock()
    frontier = _frontier()
    execution = _execution(frontier)
    active = MagicMock()
    active.id = uuid4()
    active.node_ids = ["node-b", "node-c"]

    completed_lookup = MagicMock()
    completed_lookup.scalar_one_or_none.return_value = None
    execution_lookup = MagicMock()
    execution_lookup.scalar_one_or_none.return_value = execution
    overlap_lookup = MagicMock()
    overlap_lookup.scalars.return_value.all.return_value = [active]
    db.execute.side_effect = [completed_lookup, execution_lookup, overlap_lookup]

    next_identity = MagicMock()
    next_identity.execution_id = frontier.execution_id
    next_identity.workflow_version_id = frontier.workflow_version_id
    next_identity.node_ids = ("node-a", "node-b")
    next_identity.key.return_value = "frontier-next"

    with patch(
        "app.services.workflow.frontier_progression.transition_owned_frontier",
        new_callable=AsyncMock,
    ) as transition, patch(
        "app.services.workflow.frontier_progression.WorkflowExecutionCheckpointService.append_next_in_transaction",
        new_callable=AsyncMock,
    ) as append, patch(
        "app.services.workflow.frontier_progression.enqueue_frontier",
        new_callable=AsyncMock,
    ) as enqueue:
        with pytest.raises(FrontierProgressionContractError, match="Node 重叠"):
            await complete_frontier_with_checkpoint(
                db,
                frontier=frontier,
                worker_owner="worker-a",
                attempt=2,
                checkpoint_state={"done": True},
                checkpoint_reason="frontier_completed",
                next_identity=next_identity,
                now=datetime(2026, 8, 27, 8, 0),
            )

    transition.assert_awaited_once()
    append.assert_awaited_once()
    enqueue.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_next_frontier_allows_disjoint_parallel_node_set() -> None:
    db = AsyncMock()
    frontier = _frontier()
    execution = _execution(frontier)
    active = MagicMock()
    active.id = uuid4()
    active.node_ids = ["node-c", "node-d"]

    completed_lookup = MagicMock()
    completed_lookup.scalar_one_or_none.return_value = None
    execution_lookup = MagicMock()
    execution_lookup.scalar_one_or_none.return_value = execution
    overlap_lookup = MagicMock()
    overlap_lookup.scalars.return_value.all.return_value = [active]
    db.execute.side_effect = [completed_lookup, execution_lookup, overlap_lookup]

    checkpoint = MagicMock()
    next_frontier = MagicMock()
    next_identity = MagicMock()
    next_identity.execution_id = frontier.execution_id
    next_identity.workflow_version_id = frontier.workflow_version_id
    next_identity.node_ids = ("node-a", "node-b")
    next_identity.key.return_value = "frontier-next"

    with patch(
        "app.services.workflow.frontier_progression.transition_owned_frontier",
        new_callable=AsyncMock,
    ), patch(
        "app.services.workflow.frontier_progression.WorkflowExecutionCheckpointService.append_next_in_transaction",
        new_callable=AsyncMock,
    ) as append, patch(
        "app.services.workflow.frontier_progression.enqueue_frontier",
        new_callable=AsyncMock,
    ) as enqueue:
        append.return_value = checkpoint
        enqueue.return_value = next_frontier
        result = await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=2,
            checkpoint_state={"done": True},
            checkpoint_reason="frontier_completed",
            next_identity=next_identity,
            now=datetime(2026, 8, 27, 8, 0),
        )

    assert result == (checkpoint, next_frontier)
    enqueue.assert_awaited_once()
    db.commit.assert_not_awaited()
