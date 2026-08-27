"""Workflow Worker 租约失效控制的单元测试。"""

import asyncio

import pytest

from app.services.workflow_worker.lease_guard import (
    WorkflowWorkerLeaseGuard,
    WorkflowWorkerLeaseLost,
)


@pytest.mark.asyncio
async def test_runtime_is_cancelled_when_lease_is_lost() -> None:
    """验证 lease 明确失效后 Runtime 会被主动取消，而不是继续运行。"""
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def renew_lease() -> bool:
        await started.wait()
        return False

    async def runtime() -> None:
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    guard = WorkflowWorkerLeaseGuard(renew_lease, interval_seconds=0.001)
    with pytest.raises(WorkflowWorkerLeaseLost):
        await guard.run(runtime())

    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_runtime_result_wins_over_lease_monitor() -> None:
    """验证 Runtime 已完成时不会被随后取消的 lease 监督任务影响结果。"""
    calls = 0

    async def renew_lease() -> bool:
        nonlocal calls
        calls += 1
        return True

    async def runtime() -> str:
        return "completed"

    guard = WorkflowWorkerLeaseGuard(renew_lease, interval_seconds=0.001)
    assert await guard.run(runtime()) == "completed"


@pytest.mark.asyncio
async def test_transient_lease_error_does_not_abort_runtime() -> None:
    """验证单次 heartbeat 异常不会被误判为 ownership 丢失。"""
    attempts = 0

    async def renew_lease() -> bool:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary database error")
        return True

    async def runtime() -> str:
        await asyncio.sleep(0.003)
        return "completed"

    guard = WorkflowWorkerLeaseGuard(renew_lease, interval_seconds=0.001)
    assert await guard.run(runtime()) == "completed"
    assert attempts >= 2
