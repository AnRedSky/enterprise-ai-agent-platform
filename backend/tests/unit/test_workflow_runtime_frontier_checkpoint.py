"""Workflow Runtime Multi-frontier Checkpoint 边界单元测试。

职责：验证全部 frontier Branch 成功后必须追加 Execution-level `frontier_completed` Checkpoint。
边界：只 mock DAG Executor / Checkpoint Service，不连接 PostgreSQL、不启动 Worker、不调用 Provider。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.runtime.workflow.runtime import WorkflowRuntime
from app.services.workflow.checkpoint.recovery.dag_executor import WorkflowDagMultiFrontierExecutionResult


@pytest.mark.asyncio
async def test_multi_frontier_runtime_persists_execution_level_checkpoint_after_join_ready() -> None:
    runtime = object.__new__(WorkflowRuntime)
    runtime.db = AsyncMock()
    execution = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        status="running",
        worker_owner="worker-a",
        worker_attempt=7,
    )
    service = SimpleNamespace()

    async def fake_checkpoint_writer(_node_id: str, _output: dict) -> None:
        return None

    result = WorkflowDagMultiFrontierExecutionResult(
        branch_results=(),
        merged_state_data={"left": 1, "right": 2},
        join_ready=True,
    )
    checkpoint_service = SimpleNamespace(append_next_in_transaction=AsyncMock())

    with patch(
        "app.runtime.workflow.runtime.WorkflowDagMultiFrontierExecutor.execute",
        new=AsyncMock(return_value=result),
    ), patch(
        "app.runtime.workflow.runtime.WorkflowExecutionCheckpointService",
        return_value=checkpoint_service,
    ):
        actual = await runtime._execute_multi_frontier(
            service,
            execution,
            SimpleNamespace(frontier_node_ids=("left", "right")),
            {"left": {}, "right": {}},
            uuid4(),
            False,
            30_000,
            0,
            0.0,
            [0],
        )

    assert actual.join_ready is True
    checkpoint_service.append_next_in_transaction.assert_awaited_once_with(
        execution_id=execution.id,
        execution_status="running",
        state_data={"left": 1, "right": 2},
        checkpoint_reason="frontier_completed",
        worker_owner="worker-a",
        expected_worker_owner="worker-a",
        expected_worker_attempt=7,
        tenant_id=execution.tenant_id,
    )


@pytest.mark.asyncio
async def test_multi_frontier_runtime_does_not_checkpoint_when_join_not_ready() -> None:
    runtime = object.__new__(WorkflowRuntime)
    runtime.db = AsyncMock()
    execution = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        status="running",
        worker_owner="worker-a",
        worker_attempt=7,
    )
    service = SimpleNamespace()
    result = WorkflowDagMultiFrontierExecutionResult(
        branch_results=(),
        merged_state_data=None,
        join_ready=False,
    )
    checkpoint_service = SimpleNamespace(append_next_in_transaction=AsyncMock())

    with patch(
        "app.runtime.workflow.runtime.WorkflowDagMultiFrontierExecutor.execute",
        new=AsyncMock(return_value=result),
    ), patch(
        "app.runtime.workflow.runtime.WorkflowExecutionCheckpointService",
        return_value=checkpoint_service,
    ):
        actual = await runtime._execute_multi_frontier(
            service,
            execution,
            SimpleNamespace(frontier_node_ids=("left", "right")),
            {"left": {}, "right": {}},
            uuid4(),
            False,
            30_000,
            0,
            0.0,
            [0],
        )

    assert actual.join_ready is False
    checkpoint_service.append_next_in_transaction.assert_not_awaited()
