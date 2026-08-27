"""Lease-aware Worker Runtime 集成单元测试。"""

import asyncio

import pytest

from app.services.workflow.checkpoint.recovery.observability import (
    RECOVERY_WORKER_FINISHED,
    WorkflowRecoveryEvent,
    WorkflowRecoveryTelemetry,
)
from app.services.workflow_worker.durable_frontier_execution import PlannerDrivenDurableFrontierWorkflowWorker
from app.services.workflow_worker.lease_runtime import LeaseAwareWorkflowWorker
from app.services.workflow_worker.runtime import WorkflowWorker as BaseWorkflowWorker


@pytest.mark.asyncio
async def test_default_worker_runtime_aborts_when_lease_is_lost(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证 Lease-aware Worker Runtime 入口会主动取消底层 Runtime。"""
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


@pytest.mark.asyncio
async def test_lease_loss_marks_worker_finished_as_aborted(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证主动中止场景的 Worker finished telemetry 不会错误记录为 completed。"""
    events: list[WorkflowRecoveryEvent] = []

    async def fake_execute(self: BaseWorkflowWorker, execution_id):
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise

    async def lease_lost(execution_id):
        return False

    telemetry = WorkflowRecoveryTelemetry(trace_sink=events.append)
    monkeypatch.setattr(BaseWorkflowWorker, "execute_claimed", fake_execute)
    worker = LeaseAwareWorkflowWorker(
        poll_interval_seconds=0.01,
        lease_seconds=1,
        telemetry=telemetry,
    )
    monkeypatch.setattr(worker, "_renew_lease_once", lease_lost)

    await worker.execute_claimed("execution-id")

    finished = [event for event in events if event.event_name == RECOVERY_WORKER_FINISHED]
    assert len(finished) == 1
    assert finished[0].outcome == "aborted"
    assert finished[0].reason_code == "WORKER_LEASE_LOST"


def test_package_worker_is_durable_frontier_worker() -> None:
    """默认公开 Worker 必须是 PlannerDriven Durable Frontier Worker。"""
    from app.services.workflow_worker import WorkflowWorker

    assert WorkflowWorker is PlannerDrivenDurableFrontierWorkflowWorker
