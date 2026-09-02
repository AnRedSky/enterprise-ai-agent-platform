"""Phase 2.10-II Durable Resume Operator Action 幂等真实 PostgreSQL 验收。

职责：验证同一失败 Execution 与同一 Durable Checkpoint 的 Operator Resume 重放只产生一个 Operator Action 和一条 Operator Audit。
边界：不启动 API、Scheduler、Worker、PostgreSQL 或 Redis；测试身份、Workflow、Execution 与 Checkpoint 均自动生成。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select

from app.infrastructure.db.session import SessionLocal
from app.models.core import AuditLog, Tenant, User
from app.models.integration_event import IntegrationEventRecord
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.runtime_operations.audit_trace_correlation import RuntimeAuditTraceCorrelationService
from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_resume_operator_action_replay_reuses_result_and_audit() -> None:
    """验证同一 Checkpoint 的 Resume 重放不会重复创建 Operator Action 或 Audit。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    workflow_id = uuid.uuid4()
    version_id = uuid.uuid4()
    execution_id = uuid.uuid4()

    try:
        async with SessionLocal() as db:
            tenant = Tenant(id=tenant_id, name=f"phase-210-resume-{suffix}", status="active")
            user = User(
                id=user_id,
                username=f"phase-210-resume-user-{suffix}",
                password_hash="test",
                tenant_id=tenant_id,
            )
            workflow = Workflow(
                id=workflow_id,
                tenant_id=tenant_id,
                owner_id=user_id,
                name=f"phase-210-resume-workflow-{suffix}",
                status="draft",
                published_version_id=None,
            )
            version = WorkflowVersion(
                id=version_id,
                workflow_id=workflow_id,
                version="1.0.0",
                created_by=user_id,
                definition={
                    "nodes": [{"id": "input", "type": "input", "config": {}}],
                    "config": {},
                },
                status="published",
            )
            db.add_all([tenant, user, workflow, version])
            await db.flush()
            workflow.status = "published"
            workflow.published_version_id = version_id
            db.add(WorkflowExecution(
                id=execution_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                workflow_version_id=version_id,
                created_by=user_id,
                status="failed",
                input_data={"phase": "2.10-II", "scenario": "resume_idempotency"},
                error_code="NODE_TIMEOUT",
            ))
            await db.flush()
            db.add(WorkflowExecutionCheckpoint(
                execution_id=execution_id,
                sequence=1,
                node_id="input",
                node_attempt=1,
                execution_status="failed",
                node_status="failed",
                state_data={"resume": "state", "sequence": 1},
                input_data={"phase": "2.10-II"},
                output_data=None,
                checkpoint_reason="node_failed",
                worker_owner=None,
                error_code="NODE_TIMEOUT",
            ))
            await db.commit()

        async with SessionLocal() as db:
            first = await OperatorActionGovernanceService(db).execute_execution(
                execution_id=execution_id,
                tenant_id=tenant_id,
                actor_id=user_id,
                is_admin=True,
                action="resume",
                confirm=True,
            )
            first_id = first.id
            assert first.status == "pending"
            assert first.resume_of_execution_id == execution_id
            assert first.resume_checkpoint_sequence == 1

        async with SessionLocal() as db:
            replay = await OperatorActionGovernanceService(db).execute_execution(
                execution_id=execution_id,
                tenant_id=tenant_id,
                actor_id=user_id,
                is_admin=True,
                action="resume",
                confirm=True,
            )
            assert replay.id == first_id
            assert replay.resume_of_execution_id == execution_id
            assert replay.resume_checkpoint_sequence == 1

        async with SessionLocal() as db:
            action_rows = list((await db.execute(
                select(OperatorActionIdempotency).where(
                    OperatorActionIdempotency.tenant_id == tenant_id,
                    OperatorActionIdempotency.resource_type == "workflow_execution",
                    OperatorActionIdempotency.resource_id == execution_id,
                    OperatorActionIdempotency.action == "resume",
                )
            )).scalars().all())
            assert len(action_rows) == 1
            action = action_rows[0]
            assert action.status == "succeeded"
            assert action.result_resource_type == "workflow_execution"
            assert action.result_resource_id == first_id
            assert action.idempotency_key == f"internal:resume:{execution_id}:1"

            audits = list((await db.execute(
                select(AuditLog).where(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.operator_action_id == action.id,
                    AuditLog.action == "operator.workflow_execution.resume",
                )
            )).scalars().all())
            assert len(audits) == 1
            assert audits[0].workflow_execution_id == first_id
            assert audits[0].trace_id == str(first_id)

            traces = list((await db.execute(
                select(WorkflowTraceEvent).where(
                    WorkflowTraceEvent.tenant_id == tenant_id,
                    WorkflowTraceEvent.execution_id == first_id,
                )
            )).scalars().all())
            assert any(trace.event_type == "execution.created" for trace in traces)

            correlation = await RuntimeAuditTraceCorrelationService(db).by_operator_action(
                tenant_id,
                action.id,
            )
            assert correlation is not None
            assert correlation["execution"].id == first_id
            assert correlation["focus_operator_action_id"] == action.id
            assert correlation["audits"]["total"] == 1
            assert correlation["traces"]["total"] >= 1

    finally:
        async with SessionLocal() as db:
            await db.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
            await db.execute(delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id == tenant_id))
            await db.execute(delete(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id == tenant_id))
            await db.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id == tenant_id))
            await db.execute(delete(WorkflowExecutionCheckpoint).where(WorkflowExecutionCheckpoint.execution_id == execution_id))
            await db.execute(delete(WorkflowExecution).where(WorkflowExecution.tenant_id == tenant_id))
            await db.execute(delete(WorkflowVersion).where(WorkflowVersion.workflow_id == workflow_id))
            await db.execute(delete(Workflow).where(Workflow.id == workflow_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()
