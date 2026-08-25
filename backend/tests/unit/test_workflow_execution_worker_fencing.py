"""Workflow Execution Worker ownership fencing 单元测试。"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.services.workflow.execution as execution_module
from app.services.workflow.execution import WorkflowExecutionService


class _FakeResult:
    """测试替身：返回已重新读取并加锁的 Execution。"""

    def __init__(self, execution):
        self.execution = execution

    def scalar_one_or_none(self):
        return self.execution


class _FakeAsyncSession:
    """测试替身：仅提供 ownership fencing 所需的 execute 接口。"""

    def __init__(self, execution):
        self.execution = execution

    async def execute(self, _statement):
        return _FakeResult(self.execution)


@pytest.mark.asyncio
async def test_lock_execution_rejects_stale_worker_owner(monkeypatch) -> None:
    """旧 Worker 在租约被新 Worker 接管后不得继续推进 Execution。"""
    execution_id = uuid4()
    locked = SimpleNamespace(id=execution_id, worker_owner="worker:new")
    db = _FakeAsyncSession(locked)
    monkeypatch.setattr(execution_module, "AsyncSession", _FakeAsyncSession)

    service = WorkflowExecutionService(db)  # type: ignore[arg-type]
    claimed = SimpleNamespace(id=execution_id, worker_owner="worker:old")

    with pytest.raises(HTTPException) as exc_info:
        await service._lock_execution(claimed)  # type: ignore[arg-type]

    assert exc_info.value.status_code == 409
    assert "ownership" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_lock_execution_accepts_current_worker_owner(monkeypatch) -> None:
    """当前 Worker owner 与数据库一致时允许继续执行。"""
    execution_id = uuid4()
    locked = SimpleNamespace(id=execution_id, worker_owner="worker:current")
    db = _FakeAsyncSession(locked)
    monkeypatch.setattr(execution_module, "AsyncSession", _FakeAsyncSession)

    service = WorkflowExecutionService(db)  # type: ignore[arg-type]
    claimed = SimpleNamespace(id=execution_id, worker_owner="worker:current")

    result = await service._lock_execution(claimed)  # type: ignore[arg-type]

    assert result is locked


def test_validate_run_owner_rejects_manual_run_after_worker_claim() -> None:
    """Worker 已持有 owner 时，HTTP 手动 Run 必须退出，不能进入第二个 Runtime。"""
    service = WorkflowExecutionService.__new__(WorkflowExecutionService)
    execution = SimpleNamespace(worker_owner="worker:claimed")

    with pytest.raises(HTTPException) as exc_info:
        service._validate_run_owner(execution, None)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "只有 pending Execution 可以 Run"


def test_validate_run_owner_accepts_current_worker_and_unclaimed_http_run() -> None:
    """未认领 Execution 允许 HTTP Run，已认领 Execution 只允许对应 Worker owner。"""
    service = WorkflowExecutionService.__new__(WorkflowExecutionService)

    service._validate_run_owner(SimpleNamespace(worker_owner=None), None)
    service._validate_run_owner(SimpleNamespace(worker_owner="worker:current"), "worker:current")

    with pytest.raises(HTTPException) as exc_info:
        service._validate_run_owner(SimpleNamespace(worker_owner="worker:current"), "worker:stale")

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "只有 pending Execution 可以 Run"
