"""Durable Frontier 终态与消费边界的单元测试。

验证 Frontier、Execution 与 Checkpoint 的原子推进，以及 Runtime 启动前的消费 ownership/fencing。
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
from app.services.workflow_worker.durable_frontier_execution import PlannerDrivenDurableFrontierWorkflowWorker


def _frontier() -> MagicMock:
    frontier = MagicMock()
    frontier.id = uuid4()
    frontier.execution_id = uuid4()
    frontier.workflow_version_id = uuid4()
    frontier.tenant_id = uuid4()
    frontier.frontier_key = "frontier-current"
    frontier.attempt = 3
    return frontier


@pytest.mark.asyncio
async def test_terminal_frontier_rejects_execution_owner_mismatch_before_checkpoint_write() -> None:
    db = AsyncMock()
    frontier = _frontier()
    execution = MagicMock()
    execution.status = "running"
    execution.worker_owner = "other-worker"
    execution.worker_attempt = 3
    execution.worker_lease_expires_at = datetime(2026, 8, 27, 9, 0)
    result = MagicMock()
    result.scalar_one_or_none.return_value = execution
    db.execute.return_value = result

    with patch(
        "app.services.workflow.frontier_progression.transition_owned_frontier",
        new_callable=AsyncMock,
    ) as transition, patch(
        "app.services.workflow.frontier_progression.WorkflowExecutionCheckpointService.append_next_in_transaction",
        new_callable=AsyncMock,
    ) as append:
        with pytest.raises(FrontierProgressionContractError, match="Execution Worker ownership 已失效"):
            await complete_frontier_with_checkpoint(
                db,
                frontier=frontier,
                worker_owner="worker-a",
                attempt=3,
                checkpoint_state={"done": True},
                checkpoint_reason="frontier_completed",
                now=datetime(2026, 8, 27, 8, 0),
            )

    transition.assert_not_awaited()
    append.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_terminal_frontier_requires_running_execution_before_terminalization() -> None:
    db = AsyncMock()
    frontier = _frontier()
    execution = MagicMock()
    execution.status = "completed"
    execution.worker_owner = None
    execution.worker_attempt = 3
    current_frontier = MagicMock()
    current_frontier.status = "running"
    current_result = MagicMock()
    current_result.scalar_one_or_none.return_value = current_frontier
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [current_result, execution_result]

    with patch(
        "app.services.workflow.frontier_progression.transition_owned_frontier",
        new_callable=AsyncMock,
    ) as transition:
        with pytest.raises(FrontierProgressionContractError, match="当前 lifecycle 不允许 completion"):
            await complete_frontier_with_checkpoint(
                db,
                frontier=frontier,
                worker_owner="worker-a",
                attempt=3,
                checkpoint_state={"done": True},
                checkpoint_reason="frontier_completed",
                now=datetime(2026, 8, 27, 8, 0),
            )

    transition.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_terminal_frontier_keeps_execution_running_and_uses_worker_fencing_for_checkpoint() -> None:
    db = AsyncMock()
    frontier = _frontier()
    execution = MagicMock()
    execution.status = "running"
    execution.worker_owner = "worker-a"
    execution.worker_attempt = 3
    execution.worker_lease_expires_at = datetime(2026, 8, 27, 9, 0)
    execution.created_by = uuid4()
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    current_frontier_result = MagicMock()
    current_frontier_result.scalar_one_or_none.return_value = None
    active_frontiers_result = MagicMock()
    active_frontiers_result.scalars.return_value.all.return_value = []
    db.execute.side_effect = [current_frontier_result, execution_result, MagicMock(), active_frontiers_result]
    checkpoint = MagicMock()
    next_frontier = MagicMock()
    next_identity = MagicMock()
    next_identity.execution_id = frontier.execution_id
    next_identity.workflow_version_id = frontier.workflow_version_id
    next_identity.node_ids = ("node-b",)
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
        append.return_value = checkpoint
        enqueue.return_value = next_frontier
        result = await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner="worker-a",
            attempt=3,
            checkpoint_state={"done": True},
            checkpoint_reason="frontier_completed",
            next_identity=next_identity,
            now=datetime(2026, 8, 27, 8, 0),
        )

    assert result == (checkpoint, next_frontier)
    assert append.await_args.kwargs["execution_status"] == "running"
    assert append.await_args.kwargs["expected_worker_owner"] == "worker-a"
    assert append.await_args.kwargs["expected_worker_attempt"] == 3
    enqueue.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_failure_convergence_rejects_stale_execution_owner_before_frontier_transition() -> None:
    worker = object.__new__(PlannerDrivenDurableFrontierWorkflowWorker)
    worker.owner = "worker-a"
    frontier = _frontier()
    execution = MagicMock()
    execution.status = "running"
    execution.worker_owner = "worker-b"
    execution.worker_lease_expires_at = datetime(2026, 8, 27, 9, 0)

    db = AsyncMock()
    frontier_result = MagicMock()
    frontier_result.scalar_one_or_none.return_value = frontier
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [frontier_result, execution_result]

    with patch(
        "app.services.workflow_worker.durable_frontier_execution.SessionLocal"
    ) as session_local, patch(
        "app.services.workflow_worker.durable_frontier_execution.transition_owned_frontier",
        new_callable=AsyncMock,
    ) as transition:
        context = AsyncMock()
        context.__aenter__.return_value = db
        session_local.return_value = context
        await worker._converge_failure(frontier, ValueError("boom"))

    transition.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_failure_convergence_rejects_expired_execution_lease_before_retry_or_failure() -> None:
    worker = object.__new__(PlannerDrivenDurableFrontierWorkflowWorker)
    worker.owner = "worker-a"
    frontier = _frontier()
    execution = MagicMock()
    execution.status = "running"
    execution.worker_owner = "worker-a"
    execution.worker_lease_expires_at = datetime(2026, 8, 27, 7, 0)

    db = AsyncMock()
    frontier_result = MagicMock()
    frontier_result.scalar_one_or_none.return_value = frontier
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [frontier_result, execution_result]

    with patch(
        "app.services.workflow_worker.durable_frontier_execution.SessionLocal"
    ) as session_local, patch(
        "app.services.workflow_worker.durable_frontier_execution.schedule_frontier_retry",
        new_callable=AsyncMock,
    ) as retry, patch(
        "app.services.workflow_worker.durable_frontier_execution.transition_owned_frontier",
        new_callable=AsyncMock,
    ) as transition:
        context = AsyncMock()
        context.__aenter__.return_value = db
        session_local.return_value = context
        await worker._converge_failure(frontier, TimeoutError("timeout"))

    retry.assert_not_awaited()
    transition.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_runtime_entry_rejects_stale_frontier_before_node_execution() -> None:
    worker = object.__new__(PlannerDrivenDurableFrontierWorkflowWorker)
    worker.owner = "worker-a"
    frontier = _frontier()

    with patch.object(worker, "_verify_frontier_consumption_ownership", new_callable=AsyncMock) as verify:
        verify.return_value = False
        with patch.object(worker, "_converge_failure", new_callable=AsyncMock) as converge:
            with patch.object(worker, "_renew_frontier_forever", new_callable=AsyncMock) as heartbeat:
                await worker.execute_frontier(frontier)

    verify.assert_awaited_once_with(frontier)
    converge.assert_not_awaited()
    heartbeat.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_entry_ownership_guard_requires_frontier_and_execution_active_lease() -> None:
    worker = object.__new__(PlannerDrivenDurableFrontierWorkflowWorker)
    worker.owner = "worker-a"
    frontier = _frontier()

    db = AsyncMock()
    frontier_result = MagicMock()
    frontier_result.scalar_one_or_none.return_value = frontier
    execution_result = MagicMock()
    execution_result.scalar_one_or_none.return_value = None
    db.execute.side_effect = [frontier_result, execution_result]

    with patch(
        "app.services.workflow_worker.durable_frontier_execution.SessionLocal"
    ) as session_local:
        context = AsyncMock()
        context.__aenter__.return_value = db
        session_local.return_value = context
        assert await worker._verify_frontier_consumption_ownership(frontier) is False

    db.rollback.assert_awaited_once()
