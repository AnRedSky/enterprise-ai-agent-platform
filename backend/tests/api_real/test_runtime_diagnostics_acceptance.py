"""Phase 2.10-II Worker / Scheduler Diagnostics PostgreSQL acceptance。

测试只读取现有 Durable Facts，验证租户隔离、lease 诊断和 Scheduler durable posture。
不启动或停止任何服务，测试身份与业务事实全部自动创建并清理。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from app.infrastructure.db.session import SessionLocal
from app.models.core import Tenant, User
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.models.workflow_trigger import WorkflowTrigger
from app.services.runtime_operations.diagnostics import RuntimeDiagnosticsService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_runtime_diagnostics_are_tenant_scoped_and_use_only_durable_facts() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    workflow_a, workflow_b = uuid.uuid4(), uuid.uuid4()
    version_a, version_b = uuid.uuid4(), uuid.uuid4()
    execution_a, execution_b = uuid.uuid4(), uuid.uuid4()
    frontier_running, frontier_expired, frontier_foreign = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    trigger_a, trigger_b = uuid.uuid4(), uuid.uuid4()
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-diag-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-diag-b-{suffix}", status="active"),
                User(id=user_a, username=f"phase-210-diag-a-{suffix}", password_hash="fixture", tenant_id=tenant_a, status="active"),
                User(id=user_b, username=f"phase-210-diag-b-{suffix}", password_hash="fixture", tenant_id=tenant_b, status="active"),
                Workflow(id=workflow_a, name=f"diag-a-{suffix}", description="", owner_id=user_a, tenant_id=tenant_a, status="published"),
                Workflow(id=workflow_b, name=f"diag-b-{suffix}", description="", owner_id=user_b, tenant_id=tenant_b, status="published"),
                WorkflowVersion(id=version_a, workflow_id=workflow_a, version="1", definition={}, status="published", created_by=user_a),
                WorkflowVersion(id=version_b, workflow_id=workflow_b, version="1", definition={}, status="published", created_by=user_b),
                WorkflowExecution(id=execution_a, tenant_id=tenant_a, workflow_id=workflow_a, workflow_version_id=version_a, created_by=user_a, status="running", created_at=now),
                WorkflowExecution(id=execution_b, tenant_id=tenant_b, workflow_id=workflow_b, workflow_version_id=version_b, created_by=user_b, status="running", created_at=now),
                WorkflowFrontier(id=frontier_running, tenant_id=tenant_a, execution_id=execution_a, workflow_version_id=version_a, decision_fingerprint=f"diag-running-{suffix}", frontier_key=f"diag-running-{suffix}", node_ids=["node-1"], status="running", attempt=2, worker_owner="worker-a", worker_lease_expires_at=now + timedelta(minutes=5), created_at=now),
                WorkflowFrontier(id=frontier_expired, tenant_id=tenant_a, execution_id=execution_a, workflow_version_id=version_a, decision_fingerprint=f"diag-expired-{suffix}", frontier_key=f"diag-expired-{suffix}", node_ids=["node-2"], status="failed", attempt=3, worker_owner="worker-a", worker_lease_expires_at=now - timedelta(minutes=5), error_code="FIXTURE_FAILURE", created_at=now),
                WorkflowFrontier(id=frontier_foreign, tenant_id=tenant_b, execution_id=execution_b, workflow_version_id=version_b, decision_fingerprint=f"diag-foreign-{suffix}", frontier_key=f"diag-foreign-{suffix}", node_ids=["node-3"], status="running", attempt=1, worker_owner="worker-b", worker_lease_expires_at=now + timedelta(minutes=5), created_at=now),
                WorkflowTrigger(id=trigger_a, tenant_id=tenant_a, workflow_id=workflow_a, name=f"diag-schedule-a-{suffix}", trigger_type="schedule", status="enabled", created_by=user_a, config={}),
                WorkflowTrigger(id=trigger_b, tenant_id=tenant_b, workflow_id=workflow_b, name=f"diag-schedule-b-{suffix}", trigger_type="schedule", status="enabled", created_by=user_b, config={}),
            ])
            await db.commit()

        async with SessionLocal() as db:
            service = RuntimeDiagnosticsService(db)
            worker = await service.worker(tenant_a)
            assert worker["liveness"] == "unknown"
            assert worker["liveness_reason_code"] == "NO_DURABLE_HEARTBEAT_FACT"
            assert worker["frontier"]["total"] == 2
            assert worker["leases"]["active"] == 1
            assert worker["leases"]["expired"] == 1
            assert worker["owners"] == [{"worker_owner": "worker-a", "claim_count": 2}]
            assert {row["error_code"] for row in worker["recent_errors"]} == {"FIXTURE_FAILURE"}

            scheduler = await service.scheduler(tenant_a)
            assert scheduler["liveness"] == "unknown"
            assert scheduler["liveness_reason_code"] == "NO_DURABLE_HEARTBEAT_FACT"
            assert scheduler["durable"]["enabled_scheduled_triggers"] == 1
            assert len(scheduler["triggers"]) == 1
            assert scheduler["triggers"][0]["id"] == trigger_a

            foreign = await service.worker(tenant_b)
            assert foreign["frontier"]["total"] == 1
            assert foreign["owners"] == [{"worker_owner": "worker-b", "claim_count": 1}]
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(WorkflowFrontier).where(WorkflowFrontier.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WorkflowExecution).where(WorkflowExecution.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WorkflowTrigger).where(WorkflowTrigger.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(WorkflowVersion).where(WorkflowVersion.workflow_id.in_([workflow_a, workflow_b])))
            await db.execute(delete(Workflow).where(Workflow.id.in_([workflow_a, workflow_b])))
            await db.execute(delete(User).where(User.id.in_([user_a, user_b])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()
