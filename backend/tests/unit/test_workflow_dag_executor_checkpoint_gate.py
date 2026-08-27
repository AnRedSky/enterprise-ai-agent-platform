from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.workflow.checkpoint.recovery.dag_executor import WorkflowDagMultiFrontierExecutor
from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlan


def _plan() -> WorkflowDagResumeRuntimePlan:
    return WorkflowDagResumeRuntimePlan(
        completed_node_ids=(),
        frontier_node_ids=("left", "right"),
        nodes=(
            {"id": "left", "type": "input", "config": {}},
            {"id": "right", "type": "input", "config": {}},
        ),
        state_data={},
    )


@pytest.mark.asyncio
async def test_multi_frontier_without_checkpoint_writer_cannot_be_join_ready():
    executor = AsyncMock(side_effect=[{"left": 1}, {"right": 2}])

    result = await WorkflowDagMultiFrontierExecutor.execute(
        _plan(),
        branch_state_data={"left": {"seed": 1}, "right": {"seed": 1}},
        executor=executor,
    )

    assert result.join_ready is False
    assert result.merged_state_data is None
    assert [item.node_id for item in result.branch_results] == ["left", "right"]


@pytest.mark.asyncio
async def test_multi_frontier_requires_all_branch_checkpoints_before_join_ready():
    executor = AsyncMock(side_effect=[{"left": 1}, {"right": 2}])
    checkpoint_writer = AsyncMock()

    result = await WorkflowDagMultiFrontierExecutor.execute(
        _plan(),
        branch_state_data={"left": {"seed": 1}, "right": {"seed": 1}},
        executor=executor,
        checkpoint_writer=checkpoint_writer,
    )

    assert result.join_ready is True
    assert result.merged_state_data == {"left": 1, "right": 2}
    assert checkpoint_writer.await_count == 2


@pytest.mark.asyncio
async def test_single_frontier_without_checkpoint_writer_is_not_join_ready():
    plan = WorkflowDagResumeRuntimePlan(
        completed_node_ids=(),
        frontier_node_ids=("only",),
        nodes=({"id": "only", "type": "input", "config": {}},),
        state_data={"seed": 1},
    )
    executor = AsyncMock(return_value={"done": True})

    result = await WorkflowDagMultiFrontierExecutor.execute(
        plan,
        branch_state_data={},
        executor=executor,
    )

    assert result.join_ready is False
    assert result.merged_state_data is None
    assert result.branch_results[0].state_data == {"done": True}
