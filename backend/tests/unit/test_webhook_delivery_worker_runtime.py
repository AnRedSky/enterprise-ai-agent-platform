from __future__ import annotations

import asyncio

import pytest

from app.services.integration.webhook_delivery import WebhookDeliveryWorker


class _RuntimeProbeWorker(WebhookDeliveryWorker):
    def __init__(self, jobs: int, **kwargs: object) -> None:
        super().__init__(sender=lambda *_: _never_called(), **kwargs)
        self.jobs = jobs
        self.active = 0
        self.max_active = 0
        self.completed = 0

    async def deliver_once(self) -> bool:
        if self.jobs <= 0:
            await asyncio.sleep(0)
            return False
        self.jobs -= 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.01)
            self.completed += 1
            return True
        finally:
            self.active -= 1


def _never_called() -> int:
    raise AssertionError("probe sender must not be called")


@pytest.mark.asyncio
async def test_runtime_limits_inflight_delivery_to_configured_concurrency() -> None:
    worker = _RuntimeProbeWorker(jobs=10, concurrency=3)

    await asyncio.wait_for(worker.run_forever(poll_interval=0.001), timeout=1)

    assert worker.completed == 10
    assert worker.max_active == 3


@pytest.mark.asyncio
async def test_runtime_stop_stops_new_claims_and_drains_inflight_tasks() -> None:
    worker = _RuntimeProbeWorker(jobs=4, concurrency=4)
    task = asyncio.create_task(worker.run_forever(poll_interval=0.001))
    await asyncio.sleep(0.002)
    worker.stop()
    await asyncio.wait_for(task, timeout=1)

    assert worker.completed == 4
    assert worker.active == 0


def test_runtime_rejects_invalid_concurrency() -> None:
    with pytest.raises(ValueError, match="concurrency"):
        WebhookDeliveryWorker(concurrency=0)
