"""Workflow 自动恢复 Scheduler 扫描器单元测试。

职责：验证 Scheduler 只负责发现 failed Execution 并委托 Recovery Domain，不复制恢复规则。
边界：不连接 PostgreSQL、不启动 Scheduler 进程、不创建真实 Resume Execution。
关键依赖：WorkflowRecoveryScheduler、WorkflowExecutionAutomaticRecoveryService。
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow_scheduler import recovery as recovery_module
from app.services.workflow_scheduler.recovery import WorkflowRecoveryScheduler


class _FakeResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return list(self.values)

    def scalar_one_or_none(self):
        return self.values[0] if self.values else None


class _FakeDb:
    def __init__(self, values):
        self.values = values

    async def execute(self, _query):
        return _FakeResult(self.values)


class _FakeSessionContext:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeService:
    def __init__(self, db, policy):
        self.db = db
        self.policy = policy

    async def evaluate(self, execution, now=None):
        return SimpleNamespace(
            decision=SimpleNamespace(eligible=execution.id != BLOCKED_ID),
        )

    async def recover(self, execution, now=None):
        return SimpleNamespace(resume_execution_id=None if execution.id == BLOCKED_ID else uuid4())


BLOCKED_ID = uuid4()


@pytest.mark.asyncio
async def test_recovery_scheduler_delegates_candidates_to_domain(monkeypatch) -> None:
    recovered_id = uuid4()
    executions = [SimpleNamespace(id=recovered_id), SimpleNamespace(id=BLOCKED_ID)]
    sessions = iter([_FakeDb(executions), _FakeDb([executions[0]]), _FakeDb([executions[1]])])

    def fake_session_local():
        return _FakeSessionContext(next(sessions))

    monkeypatch.setattr(recovery_module, "SessionLocal", fake_session_local)
    monkeypatch.setattr(recovery_module, "WorkflowExecutionAutomaticRecoveryService", _FakeService)

    result = await WorkflowRecoveryScheduler(scan_limit=10).scan_once(
        now=datetime(2026, 8, 26, 12, 0),
    )

    assert result.candidates == 2
    assert result.eligible == 1
    assert result.recovered == 1
    assert result.rejected == 1
    assert result.failed == 0
