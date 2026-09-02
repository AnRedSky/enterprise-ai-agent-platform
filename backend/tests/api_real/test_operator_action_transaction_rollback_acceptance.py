"""Phase 2.10-II Operator Action 事务回滚真实 PostgreSQL 验收。

职责：验证 Retry 结果资源已经生成后，如果最终 Operator Audit 写入失败，Retry Execution 与 Operator Action 幂等事实不会被半提交。
边界：不启动 API、Scheduler、Worker、PostgreSQL 或 Redis；测试身份、Workflow、Execution 和幂等键均自动生成。
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
async def test_retry_operator_action_rolls_back_when_result_audit_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证最终 Audit 失败时 Retry Execution 与 Operator Action 幂等事实一起回滚。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    workflow_id = uuid.uuid4()
    version_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    idempotency_key = f"phase-210-rollback:{suffix}"

    async def fail_audit(*args, **kwargs) -> None:
        """故意让最终 Operator Audit 写入失败，以验证外层事务边界。"""
        raise RuntimeError("simulated operator audit failure")

    try:
        async with SessionLocal() as db:
            tenant = Tenant(id=tenant_id, name=f"phase-210-rollback-{suffix}", status="active")
            user = User(
                id=user_id,
                username=f"phase-210-rollback-user-{suffix}",
                password_hash="test",
                tenant_id=tenant_id,
            )
            workflow = Workflow(
                id=workflow_id,
                tenant_id=tenant_id,
                owner_id=user_id,
                name=f"phase-210-rollback-workflow-{suffix}",
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
            db.add(
                WorkflowExecution(
                    id=execution_id,
                    tenant_id=tenant_id,
                    workflow_id=workflow_id,
                    workflow_version_id=version_id,
                    created_by=user_id,
                    status="failed",
                    input_data={"phase": "2.10-II", "scenario": "audit_rollback"},
                    error_code="NODE_TIMEOUT",
                )
            )
            await db.commit()

        monkeypatch.setattr(OperatorActionGovernanceService, "_audit", fail_audit)

        with pytest.raises(RuntimeError, match="simulated operator audit failure"):
            async with SessionLocal() as db:
                await OperatorActionGovernanceService(db).execute_execution(
                    execution_id=execution_id,
                    tenant_id=tenant_id,
                    actor_id=user_id,
                    is_admin=True,
                    action="retry",
                    confirm=True,
                    idempotency_key=idempotency_key,
                )

        async with SessionLocal() as db:
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

            audit_rows = list(
                (
                    await db.execute(
                        select(AuditLog).where(
                            AuditLog.tenant_id == tenant_id,
                            AuditLog.action == "operator.workflow_execution.retry",
                        )
                    )
                ).scalars().all()
            )
            assert audit_rows == []

            trace_rows = list(
                (
                    await db.execute(
                        select(WorkflowTraceEvent).where(
                            WorkflowTraceEvent.tenant_id == tenant_id,
                            WorkflowTraceEvent.execution_id != execution_id,
                        )
                    )
                ).scalars().all()
            )
            assert trace_rows == []

            original = await db.get(WorkflowExecution, execution_id)
            assert original is not None
            assert original.status == "failed"

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
