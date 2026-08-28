"""Durable Resume 不完整 Bootstrap 自愈单元测试。"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.resume_contract import WorkflowExecutionResumeContractService


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _DB:
    def __init__(self, values):
        self.values = iter(values)
        self.commits = 0
        self.refreshed = []

    async def execute(self, _statement):
        return _Result(next(self.values))

    async def commit(self):
        self.commits += 1

    async def refresh(self, execution):
        self.refreshed.append(execution)


@pytest.mark.asyncio
async def test_incomplete_pending_resume_is_reconciled(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner=None,
    )
    existing = SimpleNamespace(
        id=uuid4(), tenant_id=source.tenant_id, workflow_id=source.workflow_id,
        workflow_version_id=source.workflow_version_id, resume_of_execution_id=source.id,
        resume_checkpoint_sequence=7, status="pending", worker_owner=None,
    )
    db = _DB([existing, None])
    service = WorkflowExecutionResumeContractService(db)

    async def fake_latest(_execution_id, tenant_id=None):
        return SimpleNamespace(id=uuid4(), node_id=None)

    service.checkpoint.latest = fake_latest
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(
        resume_idempotency_key=f"resume:{source.id}:checkpoint:7",
        checkpoint_sequence=7,
    )

    import app.services.workflow.execution as execution_module

    class _ExecutionService:
        async def _lock_execution(self, execution):
            return execution

        async def resume_from_latest_checkpoint(self, *_args, **_kwargs):
            raise AssertionError("reconciliation must not create a second Resume")

    monkeypatch.setattr(execution_module, "WorkflowExecutionService", lambda _db: _ExecutionService())

    bootstrapped = []

    async def fake_bootstrap(**kwargs):
        bootstrapped.append(kwargs)
        return ("node-b", "node-c")

    service.bootstrap.bootstrap = fake_bootstrap

    result = await service.resume_with_outcome(source, uuid4())

    assert result.outcome == "reconciled"
    assert result.execution is existing
    assert result.idempotency_key == f"resume:{source.id}:checkpoint:7"
    assert bootstrapped[0]["source_execution"] is source
    assert bootstrapped[0]["resume_execution"] is existing
    assert db.commits == 1
    assert db.refreshed == [existing]


@pytest.mark.asyncio
async def test_incomplete_resume_with_worker_ownership_is_rejected(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner=None,
    )
    existing = SimpleNamespace(
        id=uuid4(), tenant_id=source.tenant_id, workflow_id=source.workflow_id,
        workflow_version_id=source.workflow_version_id, resume_of_execution_id=source.id,
        resume_checkpoint_sequence=7, status="pending", worker_owner="worker:other",
    )
    db = _DB([existing, None])
    service = WorkflowExecutionResumeContractService(db)

    async def fake_latest(_execution_id, tenant_id=None):
        return SimpleNamespace(id=uuid4(), node_id=None)

    service.checkpoint.latest = fake_latest
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(
        resume_idempotency_key=f"resume:{source.id}:checkpoint:7",
        checkpoint_sequence=7,
    )

    import app.services.workflow.execution as execution_module

    class _ExecutionService:
        async def _lock_execution(self, execution):
            return execution

    monkeypatch.setattr(execution_module, "WorkflowExecutionService", lambda _db: _ExecutionService())

    with pytest.raises(ValueError, match="ownership"):
        await service.resume_with_outcome(source, uuid4())

    assert db.commits == 0
