"""Workflow Worker lease fencing 单元测试。"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow_worker import WorkflowWorker


class _FakeSession:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount
        self.commits = 0
        self.rollbacks = 0
        self.statement = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement):
        self.statement = statement
        return SimpleNamespace(rowcount=self.rowcount)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_renew_lease_returns_false_without_commit_when_fencing_loses(monkeypatch: pytest.MonkeyPatch) -> None:
    """终态转换抢先发生时，heartbeat 必须把 ownership 丢失视为正常竞争结果。"""
    worker = WorkflowWorker(lease_seconds=60)
    session = _FakeSession(rowcount=0)

    class _SessionFactory:
        def __call__(self):
            return session

    monkeypatch.setattr("app.services.workflow_worker.runtime.SessionLocal", _SessionFactory())

    owned = await worker._renew_lease_once(uuid4())

    assert owned is False
    assert session.commits == 0
    assert session.rollbacks == 1


def _where_text(session: _FakeSession) -> str:
    assert session.statement is not None
    return str(session.statement.whereclause).lower()


@pytest.mark.asyncio
async def test_renew_lease_uses_atomic_owner_and_status_fencing(monkeypatch: pytest.MonkeyPatch) -> None:
    """租约 UPDATE 必须同时 fence owner、状态和未过期租约，避免 SELECT/COMMIT TOCTOU。"""
    worker = WorkflowWorker(lease_seconds=60)
    session = _FakeSession(rowcount=1)

    class _SessionFactory:
        def __call__(self):
            return session

    monkeypatch.setattr("app.services.workflow_worker.runtime.SessionLocal", _SessionFactory())

    owned = await worker._renew_lease_once(uuid4())

    assert owned is True
    assert session.commits == 1
    assert session.rollbacks == 0
    where = _where_text(session)
    assert "worker_owner" in where
    assert "status" in where
    assert "worker_lease_expires_at" in where
