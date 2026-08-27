"""Workflow Worker 租约回收单元测试。

职责：验证过期 running Execution 可以被新 Worker 原子重新认领，并保持旧 Worker ownership fencing 的前置条件。
边界：不启动 PostgreSQL、Provider 或真实 Worker 进程；数据库查询仅使用最小测试替身。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.workflow_worker.runtime as worker_runtime
from app.services.workflow_worker import WorkflowWorker


class _FakeResult:
    """提供 claim_one 所需的 SQLAlchemy scalar_one_or_none 最小契约。"""

    def __init__(self, execution):
        self.execution = execution

    def scalar_one_or_none(self):
        return self.execution


class _FakeDb:
    """记录 Worker claim 的提交与回滚行为。"""

    def __init__(self, execution):
        self.execution = execution
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, _statement):
        return _FakeResult(self.execution)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class _FakeSessionContext:
    """模拟 SessionLocal() 返回的异步上下文管理器。"""

    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


@pytest.mark.asyncio
async def test_claim_one_reclaims_expired_running_execution(monkeypatch) -> None:
    """租约已过期的 running Execution 必须被新 Worker 重新置为 pending 并换 owner。"""
    now = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)
    execution = SimpleNamespace(
        id=uuid4(),
        status="running",
        worker_owner="worker:stale",
        worker_lease_expires_at=(now - timedelta(seconds=1)).replace(tzinfo=None),
        worker_attempt=2,
        current_node_id="agent-1",
    )
    db = _FakeDb(execution)
    monkeypatch.setattr(worker_runtime, "SessionLocal", lambda: _FakeSessionContext(db))

    worker = WorkflowWorker(lease_seconds=30)
    claimed = await worker.claim_one(now=now)

    assert claimed is execution
    assert execution.status == "pending"
    assert execution.current_node_id is None
    assert execution.worker_owner == worker.owner
    assert execution.worker_lease_expires_at == now.replace(tzinfo=None) + timedelta(seconds=30)
    assert execution.worker_attempt == 3
    assert db.commits == 1
    assert db.rollbacks == 0


@pytest.mark.asyncio
async def test_claim_one_keeps_pending_execution_semantics(monkeypatch) -> None:
    """普通 pending Execution 仍按原有 claim 语义认领，不应被误判为租约回收。"""
    now = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)
    execution = SimpleNamespace(
        id=uuid4(),
        status="pending",
        worker_owner=None,
        worker_lease_expires_at=None,
        worker_attempt=0,
        current_node_id=None,
    )
    db = _FakeDb(execution)
    monkeypatch.setattr(worker_runtime, "SessionLocal", lambda: _FakeSessionContext(db))

    worker = WorkflowWorker(lease_seconds=30)
    claimed = await worker.claim_one(now=now)

    assert claimed is execution
    assert execution.status == "pending"
    assert execution.worker_owner == worker.owner
    assert execution.worker_lease_expires_at == now.replace(tzinfo=None) + timedelta(seconds=30)
    assert execution.worker_attempt == 1
    assert db.commits == 1


@pytest.mark.asyncio
async def test_claim_one_returns_none_without_available_execution(monkeypatch) -> None:
    """没有 pending 或已过期 running Execution 时不得产生新的 Worker claim。"""
    db = _FakeDb(None)
    monkeypatch.setattr(worker_runtime, "SessionLocal", lambda: _FakeSessionContext(db))

    worker = WorkflowWorker(lease_seconds=30)
    claimed = await worker.claim_one(now=datetime(2026, 8, 27, 12, 0, tzinfo=UTC))

    assert claimed is None
    assert db.commits == 0
    assert db.rollbacks == 1
