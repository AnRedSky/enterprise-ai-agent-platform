"""Phase 2.10-II Operator Action 事务边界真实 PostgreSQL 验收。

职责：验证 Retry Operator Action 在最终 Operator Audit 写入失败时不会提交 Retry Execution、幂等事实或底层 Audit/Trace。
边界：不启动 API、Scheduler、Worker、PostgreSQL 或 Redis；测试数据自动生成并在独立事务中清理。
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
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.runtime_operations.operator_governance import OperatorActionGovernanceService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_retry_operator_action_rolls_back_execution_and_idempotency_when_operator_audit_fails(monkeypatch):
    """验证最终 Operator Audit 失败时，Retry 与 Operator Action 幂等事实不会半提交。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    workflow_id = uuid.uuid4()
    version_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    idempotency_key = f"phase-210-transaction:{suffix}"

    async def fail_operator_audit(*args, **kwargs):
        raise RuntimeError("simulated operator audit failure")

    try:
        async with SessionLocal() as db:
            tenant = Tenant(id=tenant_id, name=f"phase-210-tx-{suffix}", status="active")
            user = User(
                id=user_id,
                username=f"phase-210-tx-user-{suffix}",
                password_hash="test",
                tenant_id=tenant_id,
            )
            workflow = Workflow(
                id=workflow_id,
                tenant_id=tenant_id,
                owner_id=user_id,
                name=f"phase-210-tx-workflow-{suffix}",
                status="published",
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
            db.add_all([tenant, user, workflow])
            await db.flush()
            db.add(version)
            await db.flush()
            workflow.published_version_id = version_id
            db.add(execution)
            await db.commit()

        async with SessionLocal() as db:
            service = OperatorActionGovernanceService(db)
            monkeypatch.setattr(service, "_audit", fail_operator_audit)
            with pytest.raises(RuntimeError, match="simulated operator audit failure"):
                await service.execute_execution(
                    execution_id=execution_id,
                    tenant_id=tenant_id,
                    actor_id=user_id,
                    is_admin=True,
                    action="retry",
                    confirm=True,
                    idempotency_key=idempotency_key,
                )
            await db.rollback()

            retry_rows = list(
                (
                    await db.execute(
                        select(WorkflowExecution).where(
                            WorkflowExecution.tenant_id == tenant_id,
                            WorkflowExecution.retry_of_execution_id == execution_id,
                        )
                    )
                ).scalars().all()
            )
            assert retry_rows == []

            action_rows = list(
                (
                    await db.execute(
                        select(OperatorActionIdempotency).where(
                            OperatorActionIdempotency.tenant_id == tenant_id,
                            OperatorActionIdempotency.idempotency_key == idempotency_key,
                        )
                    )
                ).scalars().all()
            )
            assert action_rows == []

            operator_audits = list(
                (
                    await db.execute(
                        select(AuditLog).where(
                            AuditLog.tenant_id == tenant_id,
                            AuditLog.action == "operator.workflow_execution.retry",
                        )
                    )
                ).scalars().all()
            )
            assert operator_audits == []

            retry_traces = list(
                (
                    await db.execute(
                        select(WorkflowTraceEvent).where(
                            WorkflowTraceEvent.tenant_id == tenant_id,
                            WorkflowTraceEvent.execution_id != execution_id,
                        )
                    )
                ).scalars().all()
            )
            assert retry_traces == []

    finally:
        async with SessionLocal() as db:
            await db.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
            await db.execute(delete(OperatorActionIdempotency).where(OperatorActionIdempotency.tenant_id == tenant_id))
            await db.execute(delete(WorkflowTraceEvent).where(WorkflowTraceEvent.tenant_id == tenant_id))
            await db.execute(delete(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id == tenant_id))
            await db.execute(delete(WorkflowExecution).where(WorkflowExecution.tenant_id == tenant_id))
            await db.execute(delete(WorkflowVersion).where(WorkflowVersion.workflow_id == workflow_id))
            await db.execute(delete(Workflow).where(Workflow.id == workflow_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()
