"""Worker Service 进程入口的关闭生命周期单元测试。

职责：验证 Worker 主循环退出后一定释放异步数据库连接池，避免事件循环关闭阶段
由连接池延迟清理触发 asyncpg CancelledError。
边界：不启动真实 Worker、不连接 PostgreSQL，只验证进程级关闭编排。
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.entrypoints import worker as worker_entrypoint


@pytest.mark.asyncio
async def test_run_worker_service_disposes_database_engine_after_worker_stops(monkeypatch) -> None:
    """验证 Worker 主循环结束后释放 AsyncEngine。"""
    worker = worker_entrypoint.WorkflowWorker()
    worker.run_forever = AsyncMock(return_value=None)
    worker.stop = lambda: None
    dispose = AsyncMock(return_value=None)

    monkeypatch.setattr(worker_entrypoint, "WorkflowWorker", lambda: worker)
    monkeypatch.setattr(worker_entrypoint, "_dispose_database_engine", dispose)

    await worker_entrypoint.run_worker_service()

    worker.run_forever.assert_awaited_once()
    dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispose_database_engine_retries_after_cancellation_and_preserves_signal(monkeypatch) -> None:
    """验证连接池释放被取消时先完成第二次 dispose，再恢复取消语义。"""
    dispose = AsyncMock(side_effect=[asyncio.CancelledError(), None])
    fake_engine = type("FakeEngine", (), {"dispose": dispose})()
    monkeypatch.setattr(worker_entrypoint, "engine", fake_engine)

    with pytest.raises(asyncio.CancelledError):
        await worker_entrypoint._dispose_database_engine()

    assert dispose.await_count == 2
