"""Recovery lifecycle closure 单元测试。"""

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
    def __init__(self, existing):
        self.existing = existing
        self.commits = 0
        self.execute_calls = 0

    async def execute(self, _statement):
        self.execute_calls += 1
        if self.execute_calls == 1:
            return _Result(self.existing)
        return _Result(None)

    async def commit(self):
        self.commits += 1

    async def refresh(self, _execution):
        return None


@pytest.mark.asyncio
async def test_resume_idempotency_hit_requires_durable_frontier(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        status="failed",
        worker_owner=None,
    )
    existing = SimpleNamespace(
        id=uuid4(),
        tenant_id=source.tenant_id,
        workflow_id=source.workflow_id,
        workflow_version_id=source.workflow_version_id,
        resume_of_execution_id=source.id,
        resume_checkpoint_sequence=7,
    )
    db = _DB(existing)
    service = WorkflowExecutionResumeContractService(db)

    service.checkpoint.latest_recovery_fact = _fake_latest_recovery_fact
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(
        resume_idempotency_key=f"resume:{source.id}:checkpoint:7",
        checkpoint_sequence=7,
    )

    class _ExecutionService:
        async def _lock_execution(self, execution):
            return execution

        async def resume_from_latest_checkpoint(self, *_args, **_kwargs):
            raise AssertionError("incomplete idempotency hit must not create a second Resume")

    import app.services.workflow.execution as execution_module
    monkeypatch.setattr(execution_module, "WorkflowExecutionService", lambda _db: _ExecutionService())

    with pytest.raises(ValueError, match="Durable Frontier 不存在"):
        await service.resume_with_outcome(source, uuid4())

    assert db.commits == 0


@pytest.mark.asyncio
async def test_resume_idempotency_hit_converges_when_frontier_exists(monkeypatch):
    source = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        status="failed",
        worker_owner=None,
    )
    existing = SimpleNamespace(
        id=uuid4(),
        tenant_id=source.tenant_id,
        workflow_id=source.workflow_id,
        workflow_version_id=source.workflow_version_id,
        resume_of_execution_id=source.id,
        resume_checkpoint_sequence=7,
    )
    db = _DB(existing)
    service = WorkflowExecutionResumeContractService(db)
    service.checkpoint.latest_recovery_fact = _fake_latest_recovery_fact
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(
        resume_idempotency_key=f"resume:{source.id}:checkpoint:7",
        checkpoint_sequence=7,
    )

    async def execute_with_frontier(statement):
        db.execute_calls += 1
        if db.execute_calls == 1:
            return _Result(existing)
        return _Result(uuid4())

    db.execute = execute_with_frontier

    class _ExecutionService:
        async def _lock_execution(self, execution):
            return execution

        async def resume_from_latest_checkpoint(self, *_args, **_kwargs):
            raise AssertionError("valid idempotency hit must not create Resume")

    import app.services.workflow.execution as execution_module
    monkeypatch.setattr(execution_module, "WorkflowExecutionService", lambda _db: _ExecutionService())

    result = await service.resume_with_outcome(source, uuid4())

    assert result.outcome == "idempotency_hit"
    assert result.execution.id == existing.id
    assert db.commits == 0


async def _fake_latest_recovery_fact(_execution_id, tenant_id=None):
    return SimpleNamespace(id=uuid4())
