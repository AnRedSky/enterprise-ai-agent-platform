"""Durable Resume transaction boundary 单元测试。"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.services.workflow.execution import WorkflowExecutionService


class _NestedTransaction:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        self.db.nested_started += 1
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.db.nested_exited += 1
        return False


class _DB:
    def __init__(self, existing):
        self.existing = existing
        self.version = SimpleNamespace(definition={})
        self.added = []
        self.rollback_calls = 0
        self.nested_started = 0
        self.nested_exited = 0
        self.execute_calls = 0

    def begin_nested(self):
        return _NestedTransaction(self)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        raise IntegrityError("INSERT", {}, RuntimeError("duplicate idempotency key"))

    async def execute(self, _statement):
        self.execute_calls += 1
        # 第一次查询读取 WorkflowVersion；第二次查询表示预检时尚不存在幂等记录；
        # 第三次查询模拟并发事务已经提交的同 key Resume Execution。
        value = self.version if self.execute_calls == 1 else None
        if self.execute_calls >= 3:
            value = self.existing
        return _Result(value)

    async def rollback(self):
        self.rollback_calls += 1


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


@pytest.mark.asyncio
async def test_resume_idempotency_race_rolls_back_only_savepoint(monkeypatch):
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
    service = WorkflowExecutionService(db)

    async def lock_execution(execution):
        return execution

    async def latest(_execution_id):
        return SimpleNamespace(id=uuid4())

    service._lock_execution = lock_execution
    service.checkpoint.latest = latest
    service.checkpoint_recovery.assess = lambda **_: SimpleNamespace(
        eligible=True,
        reason_code=None,
        resume_idempotency_key=f"resume:{source.id}:checkpoint:7",
        checkpoint_sequence=7,
        checkpoint_id=uuid4(),
        state_data={"cursor": 7},
    )
    monkeypatch.setattr(
        "app.services.workflow.execution.WorkflowRuntime.validate_definition",
        lambda *_args, **_kwargs: None,
    )

    result = await service.resume_from_latest_checkpoint(source, uuid4())

    assert result is existing
    assert db.nested_started == 1
    assert db.nested_exited == 1
    assert db.rollback_calls == 0
    assert len(db.added) == 1
