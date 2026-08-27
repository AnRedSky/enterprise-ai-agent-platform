"""Durable Frontier progression 生命周期一致性的单元测试。

验证锁定后的 Workflow Execution lifecycle 必须与本次 completion 目标一致，避免旧 Frontier
在 terminal Execution 上写入新的 Durable completion fact。
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
    return frontier


def _execution(frontier: MagicMock, status: str) -> MagicMock:
    execution = MagicMock()
    execution.id = frontier.execution_id
    execution.status = status
    execution.worker_owner = "worker-a"
    execution.worker_lease_expires_at = datetime(2026, 8, 27, 9, 0)
    execution.worker_attempt = 4
    execution.created_by = uuid4()
    return execution


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("execution_status", "next_identity"),
    [
        ("completed", MagicMock()),
        ("running", None),
    ],
)
async def test_progression_rejects_execution_lifecycle_drift(
    execution_status: str,
    next_identity: MagicMock | None,
) -> None:
    """锁定后的 Execution 状态与 progression 目标不一致时必须 fail-closed。"""
    db = AsyncMock()
    frontier = _frontier()
    execution = _execution(frontier, execution_status)

    current_lookup = MagicMock()
    current_lookup.scalar_one_or_none.return_value = None
    execution_lookup = MagicMock()
    execution_lookup.scalar_one_or_none.return_value = execution
    db.execute.side_effect = [current_lookup, execution_lookup]

    if next_identity is not None:
        next_identity.execution_id = frontier.execution_id
        next_identity.workflow_version_id = frontier.workflow_version_id
        next_identity.node_ids = ("node-next",)
        next_identity.key.return_value = "frontier-next"

    with patch(
        "app.services.workflow.frontier_progression.transition_owned_frontier",
        new_callable=AsyncMock,
    ) as transition:
        with pytest.raises(FrontierProgressionContractError, match="Execution lifecycle 与目标不一致"):
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

    transition.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_terminal_progression_uses_locked_running_execution_as_lifecycle_source() -> None:
    """终态 completion 必须在锁定并确认 running Execution 后才允许推进 Frontier。"""
    db = AsyncMock()
    frontier = _frontier()
    execution = _execution(frontier, "running")

    current_lookup = MagicMock()
    current_lookup.scalar_one_or_none.return_value = None
    execution_lookup = MagicMock()
    execution_lookup.scalar_one_or_none.return_value = execution
    sibling_lookup = MagicMock()
    sibling_lookup.scalar_one_or_none.return_value = None
    db.execute.side_effect = [current_lookup, execution_lookup, sibling_lookup]

    with patch(
        "app.services.workflow.frontier_progression.transition_owned_frontier",
        new_callable=AsyncMock,
    ) as transition, patch(
        "app.services.workflow.frontier_progression.WorkflowExecutionCheckpointService.append_next_in_transaction",
        new_callable=AsyncMock,
    ) as append:
        append.return_value = MagicMock()
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

    transition.assert_awaited_once()
    append.assert_awaited_once()
    assert execution.status == "completed"
    db.commit.assert_not_awaited()
