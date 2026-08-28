"""Recovery lifecycle closure 单元测试。"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.resume_contract import WorkflowExecutionResumeContractService


class _Result:
    def __init__(self, value): self.value = value
    def scalar_one_or_none(self): return self.value


class _DB:
    def __init__(self, existing): self.existing = existing; self.commits = 0; self.execute_calls = 0
    async def execute(self, _statement):
        self.execute_calls += 1
        return _Result(self.existing if self.execute_calls == 1 else None)
    async def commit(self): self.commits += 1
    async def refresh(self, _execution): return None


@pytest.mark.asyncio
async def test_resume_idempotency_hit_reconciles_incomplete_durable_frontier(monkeypatch):
    source = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), status="failed", worker_owner=None)
    existing = SimpleNamespace(id=uuid4(), tenant_id=source.tenant_id, workflow_id=source.workflow_id, workflow_version_id=source.workflow_version_id, resume_of_execution_id=source.id, resume_checkpoint_sequence=7, status="pending", worker_owner=None)
    db = _DB(existing); service = WorkflowExecutionResumeContractService(db)
    service.checkpoint.latest_recovery_fact = _fake_latest_recovery_fact
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(resume_idempotency_key=f"resume:{source.id}:checkpoint:7", checkpoint_sequence=7)
    bootstrapped = []
    async def bootstrap(**kwargs): bootstrapped.append(kwargs)
    service.bootstrap.bootstrap = bootstrap
    class _ExecutionService:
        async def _lock_execution(self, execution): return execution
        async def resume_from_latest_checkpoint(self, *_args, **_kwargs): raise AssertionError("不完整幂等 Resume 不应创建第二个 Execution")
    import app.services.workflow.execution as execution_module
    monkeypatch.setattr(execution_module, "WorkflowExecutionService", lambda _db: _ExecutionService())
    result = await service.resume_with_outcome(source, uuid4(), commit=False)
    assert result.outcome == "reconciled"; assert result.execution.id == existing.id; assert len(bootstrapped) == 1; assert db.commits == 0


@pytest.mark.asyncio
async def test_resume_idempotency_hit_converges_when_frontier_exists(monkeypatch):
    source = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), status="failed", worker_owner=None)
    existing = SimpleNamespace(id=uuid4(), tenant_id=source.tenant_id, workflow_id=source.workflow_id, workflow_version_id=source.workflow_version_id, resume_of_execution_id=source.id, resume_checkpoint_sequence=7, status="pending", worker_owner=None)
    db = _DB(existing); service = WorkflowExecutionResumeContractService(db)
    service.checkpoint.latest_recovery_fact = _fake_latest_recovery_fact
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(resume_idempotency_key=f"resume:{source.id}:checkpoint:7", checkpoint_sequence=7)
    async def execute_with_frontier(statement):
        db.execute_calls += 1
        return _Result(existing if db.execute_calls == 1 else uuid4())
    db.execute = execute_with_frontier
    class _ExecutionService:
        async def _lock_execution(self, execution): return execution
        async def resume_from_latest_checkpoint(self, *_args, **_kwargs): raise AssertionError("有效幂等命中不应创建 Resume")
    import app.services.workflow.execution as execution_module
    monkeypatch.setattr(execution_module, "WorkflowExecutionService", lambda _db: _ExecutionService())
    result = await service.resume_with_outcome(source, uuid4())
    assert result.outcome == "idempotency_hit"; assert result.execution.id == existing.id; assert db.commits == 0


async def _fake_latest_recovery_fact(_execution_id, tenant_id=None):
    return SimpleNamespace(id=uuid4())
