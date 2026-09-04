"""Operator Execution Retry / Resume PostgreSQL 并发验收。"""

from __future__ import annotations

import asyncio
import os
from functools import partial
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select

from app.infrastructure.db import SessionLocal
from app.infrastructure.db.session import engine
from app.models.core import AuditLog, Tenant, User
from app.models.integration_event import IntegrationEventRecord
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService

pytestmark = pytest.mark.integration

@pytest.fixture(autouse=True)
def require_database_integration() -> None:
    if os.getenv("RUN_DATABASE_INTEGRATION") != "1":
        pytest.skip("需要设置 RUN_DATABASE_INTEGRATION=1 才执行 Operator Execution PostgreSQL 并发验收")

@pytest_asyncio.fixture(autouse=True)
async def reset_database_engine_pool() -> None:
    await engine.dispose()
    try:
        yield
    finally:
        await engine.dispose()

async def _create_failed_execution(tenant_id, user_id, *, with_checkpoint: bool = False):
    workflow_id, version_id, execution_id = uuid4(), uuid4(), uuid4()
    async with SessionLocal() as session:
        async with session.begin():
            workflow = Workflow(id=workflow_id, name=f"operator-concurrency-{workflow_id}", owner_id=user_id, tenant_id=tenant_id, status="published", published_version_id=None)
            session.add(workflow); await session.flush()
            version = WorkflowVersion(id=version_id, workflow_id=workflow_id, version="1", definition={"config": {}, "nodes": [{"id": "input", "type": "input", "config": {}}], "edges": []}, status="published", created_by=user_id)
            session.add(version); await session.flush(); workflow.published_version_id = version_id
            execution = WorkflowExecution(id=execution_id, tenant_id=tenant_id, workflow_id=workflow_id, workflow_version_id=version_id, created_by=user_id, status="failed", input_data={"source": "operator-concurrency"}, error_code="TEST_FAILED")
            session.add(execution); await session.flush()
            if with_checkpoint:
                session.add(WorkflowExecutionCheckpoint(execution_id=execution_id, sequence=0, execution_status="running", node_id="input", node_status="completed", node_attempt=1, state_data={"input": {"value": "checkpoint"}}, input_data={"source": "operator-concurrency"}, output_data={"value": "checkpoint"}, checkpoint_reason="node.completed"))
    return workflow_id, version_id, execution_id

async def _create_identity():
    tenant_id, user_id = uuid4(), uuid4()
    async with SessionLocal() as session:
        async with session.begin():
            session.add(Tenant(id=tenant_id, name=f"operator-concurrency-{tenant_id}"))
            session.add(User(id=user_id, username=f"operator-concurrency-{user_id}", password_hash="integration-test", tenant_id=tenant_id))
    return tenant_id, user_id

async def _execute_concurrently(*, execution_id, tenant_id, user_id, action, confirm, idempotency_key=None):
    barrier = asyncio.Barrier(2)
    async def invoke():
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session); await barrier.wait()
            try:
                result = await service.execute_execution(execution_id, tenant_id, user_id, True, action, confirm=confirm, idempotency_key=idempotency_key)
                return ("replay_or_success", result.id)
            except Exception as exc:
                await session.rollback(); return ("error", getattr(exc, "status_code", None), str(exc))
    return await asyncio.gather(invoke(), invoke())

async def _cleanup(tenant_id, user_id) -> None:
    async with SessionLocal() as session:
        await session.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
        await session.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id == tenant_id))
        await session.execute(delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id == tenant_id))
        await session.execute(delete(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id == tenant_id))
        await session.execute(delete(WorkflowExecutionCheckpoint).where(WorkflowExecutionCheckpoint.execution_id.in_(select(WorkflowExecution.id).where(WorkflowExecution.tenant_id == tenant_id))))
        await session.execute(delete(WorkflowExecution).where(WorkflowExecution.tenant_id == tenant_id))
        await session.execute(delete(WorkflowVersion).where(WorkflowVersion.created_by == user_id))
        await session.execute(delete(Workflow).where(Workflow.owner_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.execute(delete(Tenant).where(Tenant.id == tenant_id)); await session.commit()

@pytest.mark.asyncio
async def test_retry_cross_session_same_operator_action_creates_one_result_resource() -> None:
    tenant_id, user_id = await _create_identity(); _, _, execution_id = await _create_failed_execution(tenant_id, user_id); key = f"operator-retry-race-{uuid4()}"
    try:
        results = await _execute_concurrently(execution_id=execution_id, tenant_id=tenant_id, user_id=user_id, action="retry", confirm=True, idempotency_key=key)
        successful = [item for item in results if item[0] == "replay_or_success"]; errors = [item for item in results if item[0] == "error"]
        assert len(successful) == 2 or (len(successful) == 1 and len(errors) == 1 and errors[0][1] == 409)
        async with SessionLocal() as session:
            executions = list((await session.execute(select(WorkflowExecution).where(WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.retry_of_execution_id == execution_id))).scalars().all())
            idempotency = (await session.execute(select(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id == tenant_id, OperatorActionIdempotency.idempotency_key == key))).scalar_one()
            audit_count = (await session.execute(select(func.count()).select_from(AuditLog).where(AuditLog.tenant_id == tenant_id, AuditLog.operator_action_id == idempotency.id))).scalar_one()
            trace_count = (await session.execute(select(func.count()).select_from(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id == tenant_id, WorkflowTraceEvent.execution_id.in_([execution_id, executions[0].id])))).scalar_one()
            assert len(executions) == 1; assert idempotency.status == "succeeded"; assert idempotency.result_resource_type == "workflow_execution"; assert idempotency.result_resource_id == executions[0].id; assert audit_count == 1; assert trace_count == 2
            returned_ids = [item[1] for item in successful]; assert returned_ids == [executions[0].id] * len(returned_ids)
    finally: await _cleanup(tenant_id, user_id)

@pytest.mark.asyncio
async def test_resume_cross_session_same_operator_action_creates_one_result_resource() -> None:
    tenant_id, user_id = await _create_identity(); _, _, execution_id = await _create_failed_execution(tenant_id, user_id, with_checkpoint=True); key = f"resume:{execution_id}:checkpoint:0"
    try:
        results = await _execute_concurrently(execution_id=execution_id, tenant_id=tenant_id, user_id=user_id, action="resume", confirm=True, idempotency_key=key)
        successful = [item for item in results if item[0] == "replay_or_success"]; errors = [item for item in results if item[0] == "error"]
        assert len(successful) == 2 or (len(successful) == 1 and len(errors) == 1 and errors[0][1] == 409)
        async with SessionLocal() as session:
            executions = list((await session.execute(select(WorkflowExecution).where(WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.resume_of_execution_id == execution_id))).scalars().all())
            idempotency = (await session.execute(select(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id == tenant_id, OperatorActionIdempotency.idempotency_key == key))).scalar_one()
            audit_count = (await session.execute(select(func.count()).select_from(AuditLog).where(AuditLog.tenant_id == tenant_id, AuditLog.operator_action_id == idempotency.id))).scalar_one()
            trace_count = (await session.execute(select(func.count()).select_from(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id == tenant_id, WorkflowTraceEvent.execution_id.in_([execution_id, executions[0].id])))).scalar_one()
            assert len(executions) == 1; assert executions[0].resume_checkpoint_sequence == 0; assert executions[0].idempotency_key == key; assert idempotency.status == "succeeded"; assert idempotency.result_resource_type == "workflow_execution"; assert idempotency.result_resource_id == executions[0].id; assert audit_count == 1; assert trace_count == 2
            returned_ids = [item[1] for item in successful]; assert returned_ids == [executions[0].id] * len(returned_ids)
    finally: await _cleanup(tenant_id, user_id)

async def _raise_after_audit(service: OperatorActionGovernanceService, *args, **kwargs):
    await OperatorActionGovernanceService._audit(service, *args, **kwargs); raise RuntimeError("operator audit failure")

@pytest.mark.asyncio
async def test_retry_rolls_back_execution_and_governance_facts_when_finalization_fails(monkeypatch) -> None:
    tenant_id, user_id = await _create_identity(); _, _, execution_id = await _create_failed_execution(tenant_id, user_id); key = f"operator-retry-rollback-{uuid4()}"
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session); monkeypatch.setattr(service, "_audit", AsyncMock(side_effect=partial(_raise_after_audit, service)))
            with pytest.raises(RuntimeError, match="operator audit failure"):
                await service.execute_execution(execution_id, tenant_id, user_id, True, "retry", confirm=True, idempotency_key=key)
        async with SessionLocal() as session:
            executions = list((await session.execute(select(WorkflowExecution).where(WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.retry_of_execution_id == execution_id))).scalars().all())
            idempotency = list((await session.execute(select(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id == tenant_id, OperatorActionIdempotency.idempotency_key == key))).scalars().all())
            audits = list((await session.execute(select(AuditLog).where(AuditLog.tenant_id == tenant_id, AuditLog.action == "operator.workflow_execution.retry"))).scalars().all())
            traces = list((await session.execute(select(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id == tenant_id, WorkflowTraceEvent.execution_id == execution_id))).scalars().all())
            assert executions == []; assert idempotency == []; assert audits == []; assert traces == []
    finally: await _cleanup(tenant_id, user_id)

@pytest.mark.asyncio
async def test_resume_rolls_back_execution_and_governance_facts_when_finalization_fails(monkeypatch) -> None:
    tenant_id, user_id = await _create_identity(); _, _, execution_id = await _create_failed_execution(tenant_id, user_id, with_checkpoint=True); key = f"resume:{execution_id}:checkpoint:0:rollback"
    try:
        async with SessionLocal() as session:
            service = OperatorActionGovernanceService(session); monkeypatch.setattr(service, "_audit", AsyncMock(side_effect=partial(_raise_after_audit, service)))
            with pytest.raises(RuntimeError, match="operator audit failure"):
                await service.execute_execution(execution_id, tenant_id, user_id, True, "resume", confirm=True, idempotency_key=key)
        async with SessionLocal() as session:
            executions = list((await session.execute(select(WorkflowExecution).where(WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.resume_of_execution_id == execution_id))).scalars().all())
            idempotency = list((await session.execute(select(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id == tenant_id, OperatorActionIdempotency.idempotency_key == key))).scalars().all())
            audits = list((await session.execute(select(AuditLog).where(AuditLog.tenant_id == tenant_id, AuditLog.action == "operator.workflow_execution.resume"))).scalars().all())
            traces = list((await session.execute(select(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id == tenant_id, WorkflowTraceEvent.execution_id == execution_id))).scalars().all())
            assert executions == []; assert idempotency == []; assert audits == []; assert traces == []
    finally: await _cleanup(tenant_id, user_id)
