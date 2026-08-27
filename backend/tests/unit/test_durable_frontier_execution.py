"""Durable Frontier Worker 的 Multi-frontier Checkpoint 边界单元测试。

验证 Durable Frontier 由统一 progression primitive 负责 frontier_completed Checkpoint，
Worker Adapter 不再通过共享 WorkflowRuntime 的 Multi-frontier helper 重复追加完成快照。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.workflow_worker.durable_frontier_execution import (
    PlannerDrivenDurableFrontierWorkflowWorker,
)


@pytest.mark.asyncio
async def test_durable_multi_frontier_adapter_does_not_append_checkpoint() -> None:
    """Durable Multi-frontier 只写 Node facts，完成快照由外层 progression 统一提交。"""
    worker = PlannerDrivenDurableFrontierWorkflowWorker(concurrency=1)
    runtime = MagicMock()
    runtime._execute_node_with_policy = AsyncMock(return_value={"content": "ok"})
    service = MagicMock()
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    plan = SimpleNamespace(frontier_node_ids=("branch-a", "branch-b"), nodes=())
    result = SimpleNamespace(join_ready=True, merged_state_data={"content": "merged"})

    with patch(
        "app.services.workflow_worker.durable_frontier_execution.WorkflowDagMultiFrontierExecutor.execute",
        new_callable=AsyncMock,
        return_value=result,
    ) as execute:
        checkpoint_service = MagicMock()
        with patch(
            "app.services.workflow_worker.durable_frontier_execution.complete_frontier_with_checkpoint",
            new=checkpoint_service,
        ):
            actual = await worker._execute_multi_frontier_without_checkpoint(
                runtime,
                service,
                execution,
                plan,
                {"branch-a": {"x": 1}, "branch-b": {"x": 2}},
                uuid4(),
                False,
                30_000,
                0,
                0.0,
                [0],
            )

    assert actual is result
    execute.assert_awaited_once()
    checkpoint_service.assert_not_called()
    assert execute.await_args.kwargs["checkpoint_writer"] is not None


@pytest.mark.asyncio
async def test_durable_multi_frontier_adapter_reuses_runtime_node_execution() -> None:
    """Adapter 必须继续委托唯一 WorkflowRuntime 的 Node Retry / Execution 逻辑。"""
    worker = PlannerDrivenDurableFrontierWorkflowWorker(concurrency=1)
    runtime = MagicMock()
    runtime._execute_node_with_policy = AsyncMock(return_value={"content": "ok"})
    service = MagicMock()
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    plan = SimpleNamespace(frontier_node_ids=("branch-a",), nodes=())

    async def run_executor(plan, branch_state_data, executor, checkpoint_writer):
        node = {"id": "branch-a", "type": "output", "config": {}}
        output = await executor(node, {"input": "x"})
        await checkpoint_writer("branch-a", output)
        return SimpleNamespace(join_ready=True, merged_state_data=output)

    with patch(
        "app.services.workflow_worker.durable_frontier_execution.WorkflowDagMultiFrontierExecutor.execute",
        new=run_executor,
    ):
        result = await worker._execute_multi_frontier_without_checkpoint(
            runtime,
            service,
            execution,
            plan,
            {"branch-a": {"input": "x"}},
            uuid4(),
            False,
            30_000,
            0,
            0.0,
            [0],
        )

    assert result.join_ready is True
    runtime._execute_node_with_policy.assert_awaited_once()
    assert runtime._execute_node_with_policy.await_args.args[0] is service
    assert runtime._execute_node_with_policy.await_args.args[1] is execution
