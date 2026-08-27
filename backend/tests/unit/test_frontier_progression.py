from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_progression import complete_frontier_with_checkpoint


@pytest.mark.asyncio
async def test_complete_frontier_with_checkpoint_is_atomic_and_idempotent() -> None:
    db = AsyncMock()
    frontier = MagicMock()
    frontier.id = uuid4()
    frontier.execution_id = uuid4()
    frontier.workflow_version_id = uuid4()
    frontier.tenant_id = uuid4()
    next_identity = WorkflowFrontierIdentity(
        execution_id=frontier.execution_id,
        workflow_version_id=frontier.workflow_version_id,
        decision_fingerprint="next-decision",
        node_ids=("node-b",),
    )
    checkpoint = MagicMock()
    next_frontier = MagicMock()
    now = datetime(2026, 8, 27, 8, 0)

    with patch("app.services.workflow.frontier_progression.transition_owned_frontier", new_callable=AsyncMock) as transition, patch(
        "app.services.workflow.frontier_progression.WorkflowExecutionCheckpointService.append_next_in_transaction",
        new_callable=AsyncMock,
    ) as append, patch("app.services.workflow.frontier_progression.enqueue_frontier", new_callable=AsyncMock) as enqueue:
        append.return_value = checkpoint
        enqueue.return_value = next_frontier
        result = await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=4,
            checkpoint_state={"node": "node-a"},
            checkpoint_reason="node_completed",
            node_id="node-a",
            node_attempt=1,
            node_status="completed",
            output_data={"value": 1},
            next_identity=next_identity,
            now=now,
        )

    assert result == (checkpoint, next_frontier)
    transition.assert_awaited_once()
    append.assert_awaited_once()
    enqueue.assert_awaited_once()
    assert transition.await_args.kwargs["target_status"] == "completed"
    assert enqueue.await_args.kwargs["tenant_id"] == frontier.tenant_id
    assert enqueue.await_args.kwargs["node_ids"] == ("node-b",)
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_frontier_with_checkpoint_rejects_cross_execution_next_frontier() -> None:
    db = AsyncMock()
    frontier = MagicMock()
    frontier.execution_id = uuid4()
    frontier.workflow_version_id = uuid4()
    frontier.tenant_id = uuid4()
    next_identity = WorkflowFrontierIdentity(
        execution_id=uuid4(),
        workflow_version_id=frontier.workflow_version_id,
        decision_fingerprint="next",
        node_ids=("node-b",),
    )

    with pytest.raises(ValueError, match="同一个 Workflow Execution"):
        await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=1,
            checkpoint_state={},
            checkpoint_reason="node_completed",
            next_identity=next_identity,
            now=datetime(2026, 8, 27, 8, 0),
        )
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_terminal_frontier_creates_checkpoint_without_next_frontier() -> None:
    db = AsyncMock()
    frontier = MagicMock()
    frontier.id = uuid4()
    frontier.execution_id = uuid4()
    frontier.workflow_version_id = uuid4()
    frontier.tenant_id = uuid4()
    checkpoint = MagicMock()

    with patch("app.services.workflow.frontier_progression.transition_owned_frontier", new_callable=AsyncMock), patch(
        "app.services.workflow.frontier_progression.WorkflowExecutionCheckpointService.append_next_in_transaction",
        new_callable=AsyncMock,
    ) as append, patch("app.services.workflow.frontier_progression.enqueue_frontier", new_callable=AsyncMock) as enqueue:
        append.return_value = checkpoint
        result = await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=2,
            checkpoint_state={"done": True},
            checkpoint_reason="workflow_completed",
            now=datetime(2026, 8, 27, 8, 0),
        )

    assert result == (checkpoint, None)
    enqueue.assert_not_awaited()
    assert append.await_args.kwargs["execution_status"] == "completed"
