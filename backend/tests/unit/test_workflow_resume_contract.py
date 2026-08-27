"""Durable Resume outcome contract 单元测试。"""

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
    def __init__(self, existing=None):
        self.existing = existing
        self.queries = 0

    async def execute(self, _statement):
        self.queries += 1
        return _Result(self.existing)


@pytest.mark.asyncio
async def test_resume_contract_returns_idempotency_hit_without_creating_new_execution(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner=None,
    )
    existing = SimpleNamespace(
        id=uuid4(), tenant_id=source.tenant_id, workflow_id=source.workflow_id,
        workflow_version_id=source.workflow_version_id, resume_of_execution_id=source.id,
        resume_checkpoint_sequence=7,
    )
    db = _DB(existing=existing)
    service = WorkflowExecutionResumeContractService(db)

    async def fake_latest(_execution_id, tenant_id=None):
        return SimpleNamespace(id=uuid4())

    service.checkpoint.latest = fake_latest
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(
        resume_idempotency_key=f"resume:{source.id}:checkpoint:7",
        checkpoint_sequence=7,
    )

    class _ExecutionService:
        async def _lock_execution(self, execution):
            return execution

        async def resume_from_latest_checkpoint(self, *_args):
            raise AssertionError("idempotency hit must not create Resume")

    import app.services.workflow.execution as execution_module
    monkeypatch.setattr(execution_module, "WorkflowExecutionService", lambda _db: _ExecutionService())

    result = await service.resume_with_outcome(source, uuid4())

    assert result.outcome == "idempotency_hit"
    assert result.execution.id == existing.id
    assert result.idempotency_key == f"resume:{source.id}:checkpoint:7"


@pytest.mark.asyncio
async def test_resume_contract_rejects_idempotency_hit_with_lineage_drift():
    source = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner=None,
    )
    existing = SimpleNamespace(
        id=uuid4(), tenant_id=source.tenant_id, workflow_id=uuid4(),
        workflow_version_id=source.workflow_version_id, resume_of_execution_id=source.id,
        resume_checkpoint_sequence=7,
    )
    db = _DB(existing=existing)
    service = WorkflowExecutionResumeContractService(db)

    async def fake_latest(_execution_id, tenant_id=None):
        return await _fake_latest()

    service.checkpoint.latest = fake_latest
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(
        resume_idempotency_key=f"resume:{source.id}:checkpoint:7",
        checkpoint_sequence=7,
    )

    async def _lock(execution):
        return execution

    import app.services.workflow.execution as execution_module

    class _ExecutionService:
        _lock_execution = staticmethod(_lock)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(execution_module, "WorkflowExecutionService", lambda _db: _ExecutionService())
    try:
        with pytest.raises(ValueError, match="lineage"):
            await service.resume_with_outcome(source, uuid4())
    finally:
        monkeypatch.undo()


@pytest.mark.asyncio
async def test_resume_contract_rejects_non_deterministic_idempotency_key(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner=None,
    )
    db = _DB(existing=None)
    service = WorkflowExecutionResumeContractService(db)

    async def fake_latest(_execution_id, tenant_id=None):
        return SimpleNamespace(id=uuid4())

    service.checkpoint.latest = fake_latest
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(
        resume_idempotency_key="resume:external:key",
        checkpoint_sequence=7,
    )

    class _ExecutionService:
        async def _lock_execution(self, execution):
            return execution

    import app.services.workflow.execution as execution_module
    monkeypatch.setattr(execution_module, "WorkflowExecutionService", lambda _db: _ExecutionService())

    with pytest.raises(ValueError, match="幂等键"):
        await service.resume_with_outcome(source, uuid4())


async def _fake_latest():
    return SimpleNamespace(id=uuid4())


@pytest.mark.asyncio
async def test_resume_contract_returns_created_when_key_is_absent(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), status="failed",
        worker_owner=None,
    )
    created = SimpleNamespace(id=uuid4())
    db = _DB(existing=None)
    service = WorkflowExecutionResumeContractService(db)

    async def fake_latest(_execution_id, tenant_id=None):
        return SimpleNamespace(id=uuid4())

    service.checkpoint.latest = fake_latest
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(
        resume_idempotency_key=f"resume:{source.id}:checkpoint:7",
        checkpoint_sequence=7,
    )

    class _ExecutionService:
        async def _lock_execution(self, execution):
            return execution

        async def resume_from_latest_checkpoint(self, *_args):
            return created

    import app.services.workflow.execution as execution_module
    monkeypatch.setattr(execution_module, "WorkflowExecutionService", lambda _db: _ExecutionService())

    result = await service.resume_with_outcome(source, uuid4())

    assert result.outcome == "created"
    assert result.execution.id == created.id
    assert result.idempotency_key == f"resume:{source.id}:checkpoint:7"
