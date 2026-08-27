"""Durable Frontier progression Contract 的单元测试。

验证 Frontier → Execution Checkpoint → Next Frontier 的层级边界，以及
frontier_completed 只能作为 Execution-level snapshot 持久化。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_progression import (
    FrontierProgressionContractError,
    complete_frontier_with_checkpoint,
    validate_frontier_progression_contract,
)


def _frontier() -> MagicMock:
    frontier = MagicMock()
    frontier.id = uuid4()
    frontier.execution_id = uuid4()
    frontier.workflow_version_id = uuid4()
    frontier.tenant_id = uuid4()
    frontier.frontier_key = "current-key"
    return frontier


def test_progression_contract_rejects_self_loop_identity() -> None:
    frontier = _frontier()
    next_identity = WorkflowFrontierIdentity(
        execution_id=frontier.execution_id,
        workflow_version_id=frontier.workflow_version_id,
        decision_fingerprint="current",
        node_ids=("node-a",),
    )
    frontier.frontier_key = next_identity.key()

    with pytest.raises(FrontierProgressionContractError, match="不能与当前 Frontier 相同"):
        validate_frontier_progression_contract(
            frontier=frontier,
            next_identity=next_identity,
            execution_status="running",
        )


def test_progression_contract_requires_completed_execution_without_next_frontier() -> None:
    frontier = _frontier()

    with pytest.raises(FrontierProgressionContractError, match="必须进入 completed"):
        validate_frontier_progression_contract(
            frontier=frontier,
            next_identity=None,
            execution_status="running",
        )


def test_progression_contract_requires_running_execution_with_next_frontier() -> None:
    frontier = _frontier()
    next_identity = WorkflowFrontierIdentity(
        execution_id=frontier.execution_id,
        workflow_version_id=frontier.workflow_version_id,
        decision_fingerprint="next-decision",
        node_ids=("node-b",),
    )

    with pytest.raises(FrontierProgressionContractError, match="必须保持 running"):
        validate_frontier_progression_contract(
            frontier=frontier,
            next_identity=next_identity,
            execution_status="completed",
        )


def test_progression_contract_rejects_node_fact_on_frontier_completion() -> None:
    frontier = _frontier()

    with pytest.raises(FrontierProgressionContractError, match="不得携带 Node identity/status/input/output"):
        validate_frontier_progression_contract(
            frontier=frontier,
            next_identity=None,
            execution_status="completed",
            checkpoint_reason="frontier_completed",
            node_id="node-a",
            node_status="completed",
            output_data={"value": 1},
        )


def test_progression_contract_allows_node_fact_for_node_checkpoint() -> None:
    frontier = _frontier()

    validate_frontier_progression_contract(
        frontier=frontier,
        next_identity=None,
        execution_status="completed",
        checkpoint_reason="node_completed",
        node_id="node-a",
        node_attempt=2,
        node_status="completed",
        input_data={"value": 1},
        output_data={"value": 2},
    )


@pytest.mark.asyncio
async def test_complete_frontier_with_checkpoint_keeps_execution_checkpoint_free_of_node_fact() -> None:
    db = AsyncMock()
    frontier = _frontier()
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
            checkpoint_reason="frontier_completed",
            next_identity=next_identity,
            now=now,
        )

    assert result == (checkpoint, next_frontier)
    transition.assert_awaited_once()
    append.assert_awaited_once()
    enqueue.assert_awaited_once()
    assert transition.await_args.kwargs["target_status"] == "completed"
    assert append.await_args.kwargs["checkpoint_reason"] == "frontier_completed"
    assert append.await_args.kwargs["node_id"] is None
    assert append.await_args.kwargs["node_attempt"] is None
    assert append.await_args.kwargs["node_status"] is None
    assert append.await_args.kwargs["output_data"] is None
    assert append.await_args.kwargs["expected_worker_owner"] == "worker-a"
    assert append.await_args.kwargs["expected_worker_attempt"] == 4
    assert enqueue.await_args.kwargs["tenant_id"] == frontier.tenant_id
    assert enqueue.await_args.kwargs["node_ids"] == ("node-b",)
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_frontier_with_checkpoint_rejects_cross_execution_next_frontier() -> None:
    db = AsyncMock()
    frontier = _frontier()
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
            checkpoint_reason="frontier_completed",
            next_identity=next_identity,
            now=datetime(2026, 8, 27, 8, 0),
        )
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_terminal_frontier_creates_execution_checkpoint_without_node_fact() -> None:
    db = AsyncMock()
    frontier = _frontier()
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
            checkpoint_reason="frontier_completed",
            now=datetime(2026, 8, 27, 8, 0),
        )

    assert result == (checkpoint, None)
    enqueue.assert_not_awaited()
    assert append.await_args.kwargs["execution_status"] == "completed"
    assert append.await_args.kwargs["node_id"] is None
    assert append.await_args.kwargs["node_attempt"] is None
    assert append.await_args.kwargs["node_status"] is None
