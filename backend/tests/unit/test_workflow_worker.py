"""Workflow Worker 单元测试：验证独立消费器的并发编排与停止语义。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.services.workflow_worker import WorkflowWorker


@dataclass(frozen=True)
class _ClaimedExecution:
    """测试替身：与 WorkflowWorker.claim_one 的 Execution 契约保持一致。"""

    id: UUID


@pytest.mark.asyncio
async def test_dispatch_once_runs_each_claimed_execution_once() -> None:
    """一轮 dispatch 应为每个成功 claim 的 Execution 创建一个消费任务。"""
    worker = WorkflowWorker(poll_interval_seconds=0.01, concurrency=3, lease_seconds=30)
    execution_ids = [uuid4(), uuid4(), uuid4()]
    claimed = [_ClaimedExecution(item) for item in execution_ids]
    executed: list[str] = []

    async def fake_claim_one():
        return claimed.pop(0) if claimed else None

    async def fake_run(execution_id):
        executed.append(str(execution_id))

    worker.claim_one = fake_claim_one  # type: ignore[method-assign]
    worker._run_with_guard = fake_run  # type: ignore[method-assign]

    count = await worker.dispatch_once()

    assert count == 3
    assert set(executed) == {str(item) for item in execution_ids}
    assert len(executed) == 3


@pytest.mark.asyncio
async def test_run_forever_stops_without_restarting_after_stop() -> None:
    """stop 后 Worker 不应继续轮询。"""
    worker = WorkflowWorker(poll_interval_seconds=0.01, concurrency=1, lease_seconds=30)
    calls = 0

    async def fake_dispatch_once():
        nonlocal calls
        calls += 1
        worker.stop()
        return 0

    worker.dispatch_once = fake_dispatch_once  # type: ignore[method-assign]

    await asyncio.wait_for(worker.run_forever(), timeout=1)

    assert calls == 1
    assert worker._stop_event.is_set()


def test_worker_rejects_invalid_runtime_parameters() -> None:
    """Worker 基础并发与租约参数必须在构造阶段拒绝非法值。"""
    with pytest.raises(ValueError):
        WorkflowWorker(concurrency=0)
    with pytest.raises(ValueError):
        WorkflowWorker(lease_seconds=0)
    with pytest.raises(ValueError):
        WorkflowWorker(poll_interval_seconds=0)
