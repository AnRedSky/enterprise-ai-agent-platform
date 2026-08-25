"""Workflow Worker lease heartbeat 单元测试。"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.services.workflow_worker import WorkflowWorker


@pytest.mark.asyncio
async def test_lease_heartbeat_retries_after_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """单次 heartbeat 数据库异常不能永久终止租约刷新循环。"""
    worker = WorkflowWorker(poll_interval_seconds=0.01, concurrency=1, lease_seconds=3)
    calls = 0

    async def fake_sleep(_interval: float) -> None:
        return None

    async def fake_renew(_execution_id):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("模拟数据库瞬时异常")
        return False

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    worker._renew_lease_once = fake_renew  # type: ignore[method-assign]

    await asyncio.wait_for(worker._renew_lease_forever(uuid4()), timeout=1)

    assert calls == 2


@pytest.mark.asyncio
async def test_lease_heartbeat_stops_when_ownership_is_lost() -> None:
    """heartbeat 发现 Execution ownership 已不存在后必须立即退出。"""
    worker = WorkflowWorker(poll_interval_seconds=0.01, concurrency=1, lease_seconds=3)
    calls = 0

    async def fake_renew(_execution_id):
        nonlocal calls
        calls += 1
        return False

    worker._renew_lease_once = fake_renew  # type: ignore[method-assign]

    await asyncio.wait_for(worker._renew_lease_forever(uuid4()), timeout=1)

    assert calls == 1
