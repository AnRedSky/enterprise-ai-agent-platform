"""Workflow Execution 终态 ownership 原子释放单元测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.execution import WorkflowExecutionService


class _Result:
    """测试替身：同时提供单值查询与 Frontier 集合查询契约。"""

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return SimpleNamespace(all=lambda: [])


class _FakeDb:
    """测试替身：验证状态转换只提交一次事务并刷新对象。"""

    def __init__(self) -> None:
        self.commits = 0
        self.refreshes = 0
        self.execute = AsyncMock(return_value=_Result())

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _execution) -> None:
        self.refreshes += 1


class _FakeGovernance:
    """测试替身：记录终态转换产生的审计与 Trace。"""

    def __init__(self) -> None:
        self.traces = []
        self.audits = []

    async def trace(self, *args, **kwargs) -> None:
        self.traces.append((args, kwargs))

    async def audit(self, *args, **kwargs) -> None:
        self.audits.append((args, kwargs))


@pytest.mark.asyncio
@pytest.mark.parametrize("target_status", ["completed", "failed", "cancelled"])
async def test_terminal_transition_atomically_clears_worker_ownership(target_status: str) -> None:
    """running Execution 进入任一终态时必须同步清空 owner 与 lease。"""
    db = _FakeDb()
    service = WorkflowExecutionService.__new__(WorkflowExecutionService)
    service.db = db
    service.governance = _FakeGovernance()
    tenant_id = uuid4()
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=tenant_id, status="running", created_by=uuid4(),
        worker_owner="worker:stale", worker_attempt=1, worker_lease_expires_at=SimpleNamespace(),
        ended_at=None, current_node_id="node-1", output_data=None, error_code=None,
        error_message=None, started_at=None,
    )
    service._lock_execution = lambda value: _completed(value)  # type: ignore[method-assign]

    result = await service.transition(execution, target_status, error_code="TEST_ERROR" if target_status == "failed" else None)
    assert result.status == target_status
    assert result.worker_owner is None
    assert result.worker_lease_expires_at is None
    assert result.current_node_id is None
    assert result.ended_at is not None
    assert db.commits == 1
    assert db.refreshes == 1


async def _completed(execution):
    """返回测试用的最新、已加锁 Execution。"""
    return execution
