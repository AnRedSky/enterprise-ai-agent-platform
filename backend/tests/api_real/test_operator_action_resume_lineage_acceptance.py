"""Phase 2.10-II Durable Resume Operator Action 幂等真实 PostgreSQL 验收。

职责：验证同一失败 Execution 与同一 Durable Checkpoint 的 Operator Resume 重放只产生一个 Operator Action 和一条 Operator Audit，并验证不同 Checkpoint sequence 形成新的治理结果。
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
    """验证同一 Checkpoint 重放不会重复创建治理事实，而不同 Checkpoint 会形成新治理结果。"""
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
                # Resume 只接受 Runtime 已完成的 Checkpoint 边界；Execution 当前失败是恢复前事实。
                execution_status="running",
                node_status="completed",
                state_data={"resume": "state", "sequence": 1},
                input_data={"phase": "2.10-II"},
                output_data={"node": "completed"},
                checkpoint_reason="node.completed",
                worker_owner=None,
                error_code=None,
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

        # 第二个 Checkpoint 代表同一失败 Execution 的新可恢复边界；其 sequence 必须形成新的治理键。
        async with SessionLocal() as db:
            db.add(WorkflowExecutionCheckpoint(
                execution_id=execution_id,
                sequence=2,
                node_id="input",
                node_attempt=2,
                execution_status="running",
                node_status="completed",
                state_data={"resume": "state", "sequence": 2},
                input_data={"phase": "2.10-II", "checkpoint": 2},
                output_data={"node": "completed", "attempt": 2},
                checkpoint_reason="node.completed",
                worker_owner=None,
                error_code=None,
            ))
            await db.commit()

        async with SessionLocal() as db:
            second = await OperatorActionGovernanceService(db).execute_execution(
                execution_id=execution_id,
                tenant_id=tenant_id,
                actor_id=user_id,
                is_admin=True,
                action="resume",
                confirm=True,
            )
            assert second.id != first_id
            assert second.status == "pending"
            assert second.resume_of_execution_id == execution_id
            assert second.resume_checkpoint_sequence == 2

        async with SessionLocal() as db:
            action_rows = list((await db.execute(
                select(OperatorActionIdempotency).where(
                    OperatorActionIdempotency.tenant_id == tenant_id,
                    OperatorActionIdempotency.resource_type == "workflow_execution",
                    OperatorActionIdempotency.resource_id == execution_id,
                    OperatorActionIdempotency.action == "resume",
                ).order_by(OperatorActionIdempotency.created_at.asc())
            )).scalars().all())
            assert len(action_rows) == 2
            assert [row.idempotency_key for row in action_rows] == [
                f"internal:resume:{execution_id}:1",
                f"internal:resume:{execution_id}:2",
            ]
            assert all(row.status == "succeeded" for row in action_rows)
            assert action_rows[0].result_resource_type == "workflow_execution"
            assert action_rows[0].result_resource_id == first_id
            assert action_rows[1].result_resource_type == "workflow_execution"
            assert action_rows[1].result_resource_id == second.id

            audits = list((await db.execute(
                select(AuditLog).where(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.action == "operator.workflow_execution.resume",
                    AuditLog.operator_action_id.in_([row.id for row in action_rows]),
                ).order_by(AuditLog.created_at.asc())
            )).scalars().all())
            assert len(audits) == 2
            assert {audit.workflow_execution_id for audit in audits} == {first_id, second.id}
            assert all(audit.trace_id in {str(first_id), str(second.id)} for audit in audits)

            traces = list((await db.execute(
                select(WorkflowTraceEvent).where(
                    WorkflowTraceEvent.tenant_id == tenant_id,
                    WorkflowTraceEvent.execution_id.in_([first_id, second.id]),
                )
            )).scalars().all())
            assert any(trace.execution_id == first_id and trace.event_type == "execution.created" for trace in traces)
            assert any(trace.execution_id == second.id and trace.event_type == "execution.created" for trace in traces)

            for action, expected_execution_id in zip(action_rows, [first_id, second.id], strict=True):
                correlation = await RuntimeAuditTraceCorrelationService(db).by_operator_action(
                    tenant_id,
                    action.id,
                )
                assert correlation is not None
                assert correlation["execution"].id == expected_execution_id
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