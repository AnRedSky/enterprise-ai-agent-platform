"""Phase 2.10-II Global Runtime Operations PostgreSQL acceptance.

The acceptance test validates tenant isolation and correlation over the existing
Workflow / Execution / Frontier / Trigger durable facts. It never starts or
stops any service and creates all test data automatically.
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
from app.services.runtime_operations.global_operations import GlobalRuntimeOperationsService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_global_runtime_operations_are_tenant_scoped_and_correlatable() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    workflow_a, workflow_b = uuid.uuid4(), uuid.uuid4()
    version_a, version_b = uuid.uuid4(), uuid.uuid4()
    trigger_a, trigger_b = uuid.uuid4(), uuid.uuid4()
    execution_running, execution_failed, execution_foreign = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    frontier_running, frontier_pending, frontier_foreign = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    agent_a = uuid.uuid4()
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-global-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-global-b-{suffix}", status="active"),
                User(id=user_a, username=f"phase-210-global-a-{suffix}", password_hash="fixture", tenant_id=tenant_a, status="active"),
                User(id=user_b, username=f"phase-210-global-b-{suffix}", password_hash="fixture", tenant_id=tenant_b, status="active"),
                Workflow(id=workflow_a, name=f"global-a-{suffix}", description="", owner_id=user_a, tenant_id=tenant_a, status="published"),
                Workflow(id=workflow_b, name=f"global-b-{suffix}", description="", owner_id=user_b, tenant_id=tenant_b, status="published"),
                WorkflowVersion(id=version_a, workflow_id=workflow_a, version="1", definition={"agent_id": str(agent_a)}, status="published", created_by=user_a),
                WorkflowVersion(id=version_b, workflow_id=workflow_b, version="1", definition={}, status="published", created_by=user_b),
                WorkflowTrigger(id=trigger_a, tenant_id=tenant_a, workflow_id=workflow_a, name=f"schedule-a-{suffix}", trigger_type="schedule", status="enabled", created_by=user_a, config={}),
                WorkflowTrigger(id=trigger_b, tenant_id=tenant_b, workflow_id=workflow_b, name=f"schedule-b-{suffix}", trigger_type="schedule", status="enabled", created_by=user_b, config={}),
                WorkflowExecution(id=execution_running, tenant_id=tenant_a, workflow_id=workflow_a, workflow_version_id=version_a, created_by=user_a, status="running", worker_owner="worker-a", worker_attempt=2, worker_lease_expires_at=now + timedelta(minutes=5), started_at=now, created_at=now),
                WorkflowExecution(id=execution_failed, tenant_id=tenant_a, workflow_id=workflow_a, workflow_version_id=version_a, created_by=user_a, status="failed", error_code="FIXTURE_FAILURE", created_at=now),
                WorkflowExecution(id=execution_foreign, tenant_id=tenant_b, workflow_id=workflow_b, workflow_version_id=version_b, created_by=user_b, status="running", created_at=now),
                WorkflowFrontier(id=frontier_running, tenant_id=tenant_a, execution_id=execution_running, workflow_version_id=version_a, decision_fingerprint=f"fp-running-{suffix}", frontier_key=f"frontier-running-{suffix}", node_ids=["node-1"], status="running", attempt=2, worker_owner="worker-a", worker_lease_expires_at=now + timedelta(minutes=5), created_at=now),
                WorkflowFrontier(id=frontier_pending, tenant_id=tenant_a, execution_id=execution_failed, workflow_version_id=version_a, decision_fingerprint=f"fp-pending-{suffix}", frontier_key=f"frontier-pending-{suffix}", node_ids=["node-2"], status="pending", attempt=0, created_at=now),
                WorkflowFrontier(id=frontier_foreign, tenant_id=tenant_b, execution_id=execution_foreign, workflow_version_id=version_b, decision_fingerprint=f"fp-foreign-{suffix}", frontier_key=f"frontier-foreign-{suffix}", node_ids=["node-3"], status="running", worker_owner="worker-b", worker_lease_expires_at=now + timedelta(minutes=5), created_at=now),
            ])
            await db.commit()

        async with SessionLocal() as db:
            service = GlobalRuntimeOperationsService(db)
            overview = await service.overview(tenant_a, window_hours=24, agent_id=agent_a)

            assert overview["executions"]["total"] == 2
            assert overview["executions"]["status_counts"] == {"running": 1, "failed": 1}
            assert overview["executions"]["active_count"] == 1
            assert overview["executions"]["recovery_count"] == 1
            assert overview["workflows"]["total"] == 1
            assert overview["triggers"]["scheduled_enabled"] == 1
            assert overview["worker"]["running_frontiers"] == 1
            assert overview["worker"]["pending_frontiers"] == 1
            assert overview["worker"]["leased_frontiers"] == 1
            assert overview["worker"]["active_worker_owners"] == 1
            assert overview["scheduler"]["durable_frontier_backlog"] == 1
            assert overview["scheduler"]["liveness"] == "unknown"
            assert overview["scheduler"]["liveness_reason_code"] == "NO_DURABLE_HEARTBEAT_FACT"
            assert {item["id"] for item in overview["executions"]["items"]} == {execution_running, execution_failed}

            failed = await service.overview(tenant_a, execution_id=execution_failed)
            assert failed["executions"]["total"] == 1
            assert failed["executions"]["status_counts"] == {"failed": 1}

            foreign = await service.overview(tenant_b, window_hours=24)
            assert foreign["executions"]["total"] == 1
            assert foreign["executions"]["status_counts"] == {"running": 1}
            assert foreign["worker"]["active_worker_owners"] == 1
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
