"""Worker Service 进程入口的关闭生命周期单元测试。

职责：验证 Worker 主循环退出后一定释放异步数据库连接池，避免事件循环关闭阶段
由连接池延迟清理触发 asyncpg CancelledError。
边界：不启动真实 Worker、不连接 PostgreSQL，只验证进程级关闭编排。
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.entrypoints import worker as worker_entrypoint


@pytest.mark.asyncio
async def test_run_worker_service_disposes_database_engine_after_worker_stops(monkeypatch) -> None:
    """验证两个 Worker 主循环结束后释放 AsyncEngine。"""
    workflow_worker = MagicMock()
    workflow_worker.owner = "workflow-test-owner"
    workflow_worker.run_forever = AsyncMock(return_value=None)
    workflow_worker.stop = MagicMock()

    webhook_worker = MagicMock()
    webhook_worker.owner = "webhook-test-owner"
    webhook_worker.concurrency = 4
    webhook_worker.consumer_group = "default"
    webhook_worker.tenant_id = None
    webhook_worker.run_forever = AsyncMock(return_value=None)
    webhook_worker.stop = MagicMock()

    dispose = AsyncMock(return_value=None)
    webhook_worker_factory = MagicMock(return_value=webhook_worker)
    webhook_worker_factory.DEFAULT_CONCURRENCY = 4
    webhook_worker_factory.DEFAULT_CONSUMER_GROUP = "default"

    monkeypatch.setattr(worker_entrypoint, "WorkflowWorker", lambda: workflow_worker)
    monkeypatch.setattr(worker_entrypoint, "WebhookDeliveryWorker", webhook_worker_factory)
    monkeypatch.setattr(worker_entrypoint, "WebhookHTTPProvider", lambda: SimpleNamespace(send=AsyncMock()))
    monkeypatch.setattr(worker_entrypoint, "_dispose_database_engine", dispose)

    await worker_entrypoint.run_worker_service()

    workflow_worker.run_forever.assert_awaited_once()
    webhook_worker_factory.assert_called_once()
    constructor_kwargs = webhook_worker_factory.call_args.kwargs
    assert callable(constructor_kwargs["sender"])
    assert constructor_kwargs["concurrency"] == 4
    assert constructor_kwargs["lease_seconds"] == 60
    assert constructor_kwargs["max_attempts"] == 5
    assert constructor_kwargs["tenant_id"] is None
    assert constructor_kwargs["consumer_group"] == "default"
    webhook_worker.run_forever.assert_awaited_once_with(0.2)
    workflow_worker.stop.assert_called_once()
    webhook_worker.stop.assert_called_once()
    dispose.assert_awaited_once()


def test_worker_scope_environment(monkeypatch) -> None:
    """验证 Worker 可从环境变量获得 tenant 与 consumer group 隔离边界。"""
    tenant_id = "8f4a4f0e-5b1b-4f15-a5a2-3c6d0b4a7c11"
    monkeypatch.setenv("WEBHOOK_WORKER_TENANT_ID", tenant_id)
    monkeypatch.setenv("WEBHOOK_WORKER_CONSUMER_GROUP", "phase-2.10-i")

    assert str(worker_entrypoint._optional_uuid_env("WEBHOOK_WORKER_TENANT_ID")) == tenant_id
    assert worker_entrypoint._consumer_group_env() == "phase-2.10-i"


def test_worker_scope_environment_rejects_invalid_tenant(monkeypatch) -> None:
    """验证错误的 tenant scope 不会静默退化为全租户 Worker。"""
    monkeypatch.setenv("WEBHOOK_WORKER_TENANT_ID", "not-a-uuid")

    with pytest.raises(ValueError, match="WEBHOOK_WORKER_TENANT_ID"):
        worker_entrypoint._optional_uuid_env("WEBHOOK_WORKER_TENANT_ID")


@pytest.mark.asyncio
async def test_dispose_database_engine_preserves_cancellation_after_shielded_cleanup(monkeypatch) -> None:
    """验证主任务取消后仍完成连接池清理，并在清理结束后恢复取消语义。"""
    dispose_started = asyncio.Event()
    allow_dispose = asyncio.Event()

    async def dispose() -> None:
        dispose_started.set()
        await allow_dispose.wait()

    fake_engine = SimpleNamespace(dispose=dispose)
    monkeypatch.setattr(worker_entrypoint, "engine", fake_engine)

    task = asyncio.create_task(worker_entrypoint._dispose_database_engine())
    await dispose_started.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()

    allow_dispose.set()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_dispose_database_engine_propagates_dispose_failure(monkeypatch) -> None:
    """验证非取消型连接池清理异常不被吞掉。"""
    dispose = AsyncMock(side_effect=RuntimeError("dispose failed"))
    fake_engine = SimpleNamespace(dispose=dispose)
    monkeypatch.setattr(worker_entrypoint, "engine", fake_engine)

    with pytest.raises(RuntimeError, match="dispose failed"):
        await worker_entrypoint._dispose_database_engine()

    dispose.assert_awaited_once()
