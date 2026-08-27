"""Lease-aware Worker Runtime 集成单元测试。"""

import asyncio

import pytest

from app.services.workflow_worker.lease_runtime import LeaseAwareWorkflowWorker
from app.services.workflow_worker.runtime import WorkflowWorker as BaseWorkflowWorker


@pytest.mark.asyncio
async def test_default_worker_runtime_aborts_when_lease_is_lost(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证默认 Worker Runtime 入口会主动取消底层 Runtime。"""
    cancelled = asyncio.Event()

    async def fake_execute(self: BaseWorkflowWorker, execution_id):
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    async def lease_lost(execution_id):
        return False

    monkeypatch.setattr(BaseWorkflowWorker, "execute_claimed", fake_execute)
    worker = LeaseAwareWorkflowWorker(poll_interval_seconds=0.01, lease_seconds=1)
    monkeypatch.setattr(worker, "_renew_lease_once", lease_lost)

    await worker.execute_claimed("execution-id")

    assert cancelled.is_set()


def test_package_worker_is_lease_aware() -> None:
    """默认公开 Worker 必须是 LeaseAwareWorkflowWorker。"""
    from app.services.workflow_worker import WorkflowWorker

    assert WorkflowWorker is LeaseAwareWorkflowWorker
