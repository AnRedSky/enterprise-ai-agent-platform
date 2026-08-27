"""Workflow 自动恢复 Scheduler 扫描器单元测试。"""

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
        self.committed = False

    async def execute(self, _query):
        return _FakeResult(self.values)

    async def commit(self):
        self.committed = True


class _FakeSessionContext:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeTraceService:
    def __init__(self):
        self.trace_id = "scheduler-trace-1"
        self.started = []
        self.finished = []

    def start_scan(self, *, occurred_at=None):
        context = SimpleNamespace(trace_id=self.trace_id, execution_id=None)
        self.started.append((context, occurred_at))
        return context

    def finish_scan(self, context, **kwargs):
        self.finished.append((context, kwargs))


class _FakeService:
    parent_trace_ids = []

    def __init__(self, db, policy):
        self.db = db
        self.policy = policy

    async def recover(self, execution, now=None, parent_trace_id=None):
        self.parent_trace_ids.append(parent_trace_id)
        if execution.id == BLOCKED_ID:
            return SimpleNamespace(decision=SimpleNamespace(eligible=False), resume_execution_id=None, outcome="rejected")
        return SimpleNamespace(decision=SimpleNamespace(eligible=True), resume_execution_id=uuid4(), outcome="created")


BLOCKED_ID = uuid4()


async def _no_expired_frontiers(_db, **_kwargs):
    return []


@pytest.mark.asyncio
async def test_recovery_scheduler_delegates_candidates_to_domain(monkeypatch) -> None:
    recovered_id = uuid4()
    executions = [SimpleNamespace(id=recovered_id), SimpleNamespace(id=BLOCKED_ID)]
    sessions = iter([_FakeDb(executions), _FakeDb([executions[0]]), _FakeDb([executions[1]])])

    monkeypatch.setattr(recovery_module, "SessionLocal", lambda: _FakeSessionContext(next(sessions)))
    monkeypatch.setattr(recovery_module, "recover_expired_frontiers", _no_expired_frontiers)
    monkeypatch.setattr(recovery_module, "WorkflowExecutionAutomaticRecoveryService", _FakeService)
    trace_service = _FakeTraceService()

    result = await WorkflowRecoveryScheduler(scan_limit=10, trace_service=trace_service).scan_once(now=datetime(2026, 8, 26, 12, 0))

    assert result.candidates == 2
    assert result.eligible == 1
    assert result.recovered == 1
    assert result.created == 1
    assert result.idempotency_hit == 0
    assert result.contention == 0
    assert result.rejected == 1
    assert result.failed == 0
    assert result.expired_frontiers == 0
    assert trace_service.started[0][0].trace_id == "scheduler-trace-1"
    assert _FakeService.parent_trace_ids == ["scheduler-trace-1", "scheduler-trace-1"]
    assert trace_service.finished[0][1]["recovered"] == 1


@pytest.mark.asyncio
async def test_recovery_scheduler_classifies_idempotency_hit_as_contention(monkeypatch) -> None:
    execution = SimpleNamespace(id=uuid4())
    sessions = iter([_FakeDb([]), _FakeDb([execution]), _FakeDb([execution])])

    monkeypatch.setattr(recovery_module, "SessionLocal", lambda: _FakeSessionContext(next(sessions)))
    monkeypatch.setattr(recovery_module, "recover_expired_frontiers", _no_expired_frontiers)

    class _IdempotentService(_FakeService):
        async def recover(self, execution, now=None, parent_trace_id=None):
            self.parent_trace_ids.append(parent_trace_id)
            return SimpleNamespace(decision=SimpleNamespace(eligible=True), resume_execution_id=uuid4(), outcome="idempotency_hit")

    monkeypatch.setattr(recovery_module, "WorkflowExecutionAutomaticRecoveryService", _IdempotentService)
    result = await WorkflowRecoveryScheduler(scan_limit=10).scan_once(now=datetime(2026, 8, 26, 12, 0))

    assert result.eligible == 1
    assert result.recovered == 1
    assert result.created == 0
    assert result.idempotency_hit == 1
    assert result.contention == 1
    assert result.expired_frontiers == 0


@pytest.mark.asyncio
async def test_recovery_scheduler_emits_structured_scan_event(monkeypatch, caplog) -> None:
    execution_id = uuid4()
    execution = SimpleNamespace(id=execution_id)
    sessions = iter([_FakeDb([]), _FakeDb([execution]), _FakeDb([execution])])

    monkeypatch.setattr(recovery_module, "SessionLocal", lambda: _FakeSessionContext(next(sessions)))
    monkeypatch.setattr(recovery_module, "recover_expired_frontiers", _no_expired_frontiers)
    monkeypatch.setattr(recovery_module, "WorkflowExecutionAutomaticRecoveryService", _FakeService)
    caplog.set_level("INFO", logger=recovery_module.logger.name)

    result = await WorkflowRecoveryScheduler(scan_limit=7).scan_once(now=datetime(2026, 8, 26, 12, 0))

    assert result.recovered == 1
    record = next(record for record in caplog.records if record.message == "workflow.recovery.scan.completed")
    assert record.candidates == 1
    assert record.eligible == 1
    assert record.recovered == 1
    assert record.rejected == 0
    assert record.contention == 0
    assert record.failed == 0
    assert record.scan_limit == 7


@pytest.mark.asyncio
async def test_recovery_scheduler_reclaims_expired_frontiers_before_execution_scan(monkeypatch) -> None:
    calls = []
    expired_frontiers = [SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())]

    async def fake_recover_expired_frontiers(db, *, now, limit):
        calls.append((db, now, limit))
        return expired_frontiers

    db = _FakeDb([])
    monkeypatch.setattr(recovery_module, "SessionLocal", lambda: _FakeSessionContext(db))
    monkeypatch.setattr(recovery_module, "recover_expired_frontiers", fake_recover_expired_frontiers)

    result = await WorkflowRecoveryScheduler(scan_limit=9).scan_once(now=datetime(2026, 8, 26, 12, 0))

    assert result.expired_frontiers == 2
    assert calls[0][1] == datetime(2026, 8, 26, 12, 0)
    assert calls[0][2] == 9
    assert db.committed is True
