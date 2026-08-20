import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.core import AuditLog, Base, Tenant, User
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent
from app.services.runtime_query import RuntimeQueryService
from app.services.workflow_execution import WorkflowExecutionService


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_workflow_creation_persists_governance_audit_and_trace(db):
    tenant_id, owner_id, workflow_id, version_id = [uuid.uuid4() for _ in range(4)]
    tenant = Tenant(id=tenant_id, name=f"tenant-{tenant_id}")
    owner = User(id=owner_id, username=f"owner-{owner_id}", password_hash="x", tenant_id=tenant_id)
    workflow = Workflow(id=workflow_id, name="governed", owner_id=owner_id, tenant_id=tenant_id, status="published", published_version_id=version_id)
    version = WorkflowVersion(id=version_id, workflow_id=workflow_id, version="1.0.0", status="published", created_by=owner_id,
                              definition={"nodes": [{"id": "input", "type": "input"}, {"id": "output", "type": "output"}]})
    db.add_all([tenant, owner, workflow, version])
    await db.flush()

    execution = await WorkflowExecutionService(db).create(workflow, version, owner_id, {"input": "hello"})
    audits = (await db.execute(select(AuditLog).where(AuditLog.workflow_execution_id == execution.id))).scalars().all()
    traces = (await db.execute(select(WorkflowTraceEvent).where(WorkflowTraceEvent.execution_id == execution.id))).scalars().all()
    assert len(audits) == 1 and audits[0].action == "workflow.execution.created"
    assert len(traces) == 1 and traces[0].event_type == "execution.created"
    assert audits[0].tenant_id == tenant_id and audits[0].workflow_id == workflow_id


@pytest.mark.asyncio
async def test_owner_trace_and_audit_scope_isolated(db):
    tenant_id = uuid.uuid4()
    owner_a, owner_b = uuid.uuid4(), uuid.uuid4()
    workflow_a, workflow_b = uuid.uuid4(), uuid.uuid4()
    version_a, version_b = uuid.uuid4(), uuid.uuid4()
    db.add(Tenant(id=tenant_id, name=f"tenant-{tenant_id}"))
    db.add_all([
        User(id=owner_a, username=f"a-{owner_a}", password_hash="x", tenant_id=tenant_id),
        User(id=owner_b, username=f"b-{owner_b}", password_hash="x", tenant_id=tenant_id),
        Workflow(id=workflow_a, name="a", owner_id=owner_a, tenant_id=tenant_id, status="published", published_version_id=version_a),
        Workflow(id=workflow_b, name="b", owner_id=owner_b, tenant_id=tenant_id, status="published", published_version_id=version_b),
        WorkflowVersion(id=version_a, workflow_id=workflow_a, version="1", status="published", created_by=owner_a, definition={"nodes":[{"id":"input","type":"input"}]}),
        WorkflowVersion(id=version_b, workflow_id=workflow_b, version="1", status="published", created_by=owner_b, definition={"nodes":[{"id":"input","type":"input"}]}),
    ])
    await db.commit()
    service = WorkflowExecutionService(db)
    execution_a = await service.create(await db.get(Workflow, workflow_a), await db.get(WorkflowVersion, version_a), owner_a, {})
    execution_b = await service.create(await db.get(Workflow, workflow_b), await db.get(WorkflowVersion, version_b), owner_b, {})
    query = RuntimeQueryService(db)
    _, _, total, rows = await query.audit_logs(owner_a, False, page=1, page_size=100)
    assert total == 1 and rows[0].workflow_execution_id == execution_a.id
    assert [item.id for item in await query.workflow_trace(owner_a, False, execution_a.id, tenant_id)]
    assert await query.workflow_trace(owner_a, False, execution_b.id, tenant_id) == []
