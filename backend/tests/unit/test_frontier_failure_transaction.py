from datetime import datetime
from uuid import uuid4

import pytest

import app.services.workflow_worker.durable_frontier_execution as module
from app.models.workflow_execution import WorkflowExecution


class _Governance:
    def __init__(self, db):
        self.db = db
        self.trace_calls = []
        self.audit_calls = []

    async def trace(self, *args, **kwargs):
        self.trace_calls.append((args, kwargs))

    async def audit(self, *args, **kwargs):
        self.audit_calls.append((args, kwargs))


class _DB:
    pass


@pytest.mark.asyncio
async def test_failure_terminalization_is_transaction_local(monkeypatch):
    governance = _Governance(_DB())
    monkeypatch.setattr(module, "WorkflowGovernanceService", lambda db: governance)
    worker = object.__new__(module.PlannerDrivenDurableFrontierWorkflowWorker)
    execution = WorkflowExecution(
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        created_by=uuid4(),
        status="running",
        worker_owner="worker-a",
        worker_attempt=3,
        input_data={},
    )
    now = datetime(2026, 8, 27, 12, 0, 0)

    await worker._mark_execution_failed_in_transaction(
        _DB(), execution,
        now=now,
        error_code="WORKFLOW_EXECUTION_FAILED",
        error_message="boom",
    )

    assert execution.status == "failed"
    assert execution.ended_at == now
    assert execution.worker_owner is None
    assert execution.worker_lease_expires_at is None
    assert execution.error_code == "WORKFLOW_EXECUTION_FAILED"
    assert len(governance.trace_calls) == 1
    assert len(governance.audit_calls) == 1


@pytest.mark.asyncio
async def test_already_failed_execution_does_not_duplicate_failure_fact(monkeypatch):
    governance = _Governance(_DB())
    monkeypatch.setattr(module, "WorkflowGovernanceService", lambda db: governance)
    worker = object.__new__(module.PlannerDrivenDurableFrontierWorkflowWorker)
    execution = WorkflowExecution(
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        created_by=uuid4(),
        status="failed",
        input_data={},
    )

    await worker._mark_execution_failed_in_transaction(
        _DB(), execution,
        now=datetime(2026, 8, 27, 12, 0, 0),
        error_code="WORKFLOW_EXECUTION_FAILED",
        error_message="duplicate",
    )

    assert governance.trace_calls == []
    assert governance.audit_calls == []
