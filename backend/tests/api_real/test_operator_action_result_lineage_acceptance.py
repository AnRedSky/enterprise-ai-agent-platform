"""Phase 2.10-II Operator Action -> Audit -> Result Resource -> Execution/Trace 真实 PostgreSQL 验收。

职责：验证 Retry Operator Action 通过正式治理服务产生完整的幂等、审计、结果资源和 Runtime Trace 关联事实。
边界：不启动 API、Scheduler、Worker、PostgreSQL 或 Redis；测试身份、Workflow、Execution 和幂等键均自动生成。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select

from app.infrastructure.db.session import SessionLocal
from app.models.core import AuditLog, Tenant, User
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.runtime_operations.audit_trace_correlation import RuntimeAuditTraceCorrelationService
from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_retry_operator_action_persists_full_result_lineage():
    """验证 Retry 的 Operator Action 结果可以沿幂等事实、Audit、Execution 与 Trace 完整回溯。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    workflow_id = uuid.uuid4()
    version_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    idempotency_key = f"phase-210-retry:{suffix}"

    try:
        async with SessionLocal() as db:
            tenant = Tenant(id=tenant_id, name=f"phase-210-retry-{suffix}", status="active")
            user = User(
                id=user_id,
                username=f"phase-210-retry-user-{suffix}",
                password_hash="test",
                tenant_id=tenant_id,
            )
            workflow = Workflow(
                id=workflow_id,
                tenant_id=tenant_id,
                owner_id=user_id,
                name=f"phase-210-retry-workflow-{suffix}",
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
            execution = WorkflowExecution(
                id=execution_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                workflow_version_id=version_id,
                created_by=user_id,
                status="failed",
                input_data={"phase": "2.10-II"},
                error_code="NODE_TIMEOUT",
            )
            db.add(execution)
            await db.commit()

        async with SessionLocal() as db:
            result = await OperatorActionGovernanceService(db).execute_execution(
                execution_id=execution_id,
                tenant_id=tenant_id,
                actor_id=user_id,
                is_admin=True,
                action="retry",
                confirm=True,
                idempotency_key=idempotency_key,
            )
            retry_execution_id = result.id
            assert result.status == "pending"
            assert result.retry_of_execution_id == execution_id

        async with SessionLocal() as db:
            replay = await OperatorActionGovernanceService(db).execute_execution(
                execution_id=execution_id,
                tenant_id=tenant_id,
                actor_id=user_id,
                is_admin=True,
                action="retry",
                confirm=True,
                idempotency_key=idempotency_key,
            )
            assert replay.id == retry_execution_id
            assert replay.retry_of_execution_id == execution_id

        async with SessionLocal() as db:
            action = (
                await db.execute(
                    select(OperatorActionIdempotency).where(
                        OperatorActionIdempotency.tenant_id == tenant_id,
                        OperatorActionIdempotency.idempotency_key == idempotency_key,
                    )
                )
            ).scalar_one()
            assert action.status == "succeeded"
            assert action.resource_type == "workflow_execution"
            assert action.resource_id == execution_id
            assert action.action == "retry"
            assert action.result_resource_type == "workflow_execution"
            assert action.result_resource_id == retry_execution_id

            audits = list(
                (
                    await db.execute(
                        select(AuditLog).where(
                            AuditLog.tenant_id == tenant_id,
                            AuditLog.operator_action_id == action.id,
                        )
                    )
                ).scalars().all()
            )
            assert len(audits) == 1
            audit = audits[0]
            assert audit.action == "operator.workflow_execution.retry"
            assert audit.resource_type == "workflow_execution"
            assert audit.resource_id == str(execution_id)
            assert audit.workflow_execution_id == retry_execution_id
            assert audit.trace_id == str(retry_execution_id)

            traces = list(
                (
                    await db.execute(
                        select(WorkflowTraceEvent).where(
                            WorkflowTraceEvent.tenant_id == tenant_id,
                            WorkflowTraceEvent.execution_id == retry_execution_id,
                        )
                    )
                ).scalars().all()
            )
            assert any(trace.event_type == "execution.created" for trace in traces)

            correlation = await RuntimeAuditTraceCorrelationService(db).by_operator_action(
                tenant_id,
                action.id,
            )
            assert correlation is not None
            assert correlation["execution"].id == retry_execution_id
            assert correlation["focus_operator_action_id"] == action.id
            assert correlation["audits"]["total"] == 1
            assert correlation["audits"]["items"][0].id == audit.id
            assert correlation["traces"]["total"] >= 1

    finally:
        async with SessionLocal() as db:
            await db.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
            await db.execute(delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id == tenant_id))
            await db.execute(delete(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id == tenant_id))
            await db.execute(delete(WorkflowExecution).where(WorkflowExecution.tenant_id == tenant_id))
            await db.execute(delete(WorkflowVersion).where(WorkflowVersion.workflow_id == workflow_id))
            await db.execute(delete(Workflow).where(Workflow.id == workflow_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()
