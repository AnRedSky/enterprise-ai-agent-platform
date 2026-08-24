from datetime import datetime, UTC
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.models.core import Base, Agent, AuditLog
from app.models.execution import Execution
from app.services.runtime_query import RuntimeQueryService

@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()

async def seed(session):
    owner_a, owner_b, admin = uuid4(), uuid4(), uuid4()
    agent_a, agent_b = uuid4(), uuid4()
    exec_a, exec_b = uuid4(), uuid4()
    session.add_all([
        Agent(id=agent_a, name="agent-a", owner_id=owner_a), Agent(id=agent_b, name="agent-b", owner_id=owner_b),
        Execution(id=exec_a, request_id="req-a", trace_id="trace-a", agent_id=agent_a, status="success", started_at=datetime.now(UTC)),
        Execution(id=exec_b, request_id="req-b", trace_id="trace-b", agent_id=agent_b, status="failed", started_at=datetime.now(UTC)),
        AuditLog(id=uuid4(), actor_id=owner_a, agent_id=agent_a, action="execute", status="success"),
        AuditLog(id=uuid4(), actor_id=owner_b, agent_id=agent_b, action="execute", status="failed"),
    ])
    await session.commit()
    return owner_a, owner_b, admin, agent_a, agent_b, exec_a, exec_b

@pytest.mark.asyncio
async def test_owner_isolation_for_list_detail_and_events(db):
    owner_a, _, _, _, _, exec_a, exec_b = await seed(db)
    service = RuntimeQueryService(db)
    _, _, total, rows = await service.executions(owner_a, False, page=1, page_size=100)
    assert total == 1 and rows[0].id == exec_a
    assert await service.execution(owner_a, False, exec_b) is None
    execution, events = await service.events(owner_a, False, exec_b)
    assert execution is None and events == []

@pytest.mark.asyncio
async def test_admin_cross_owner_and_filter_matrix(db):
    _, _, admin, agent_a, _, exec_a, _ = await seed(db)
    service = RuntimeQueryService(db)
    _, _, total, rows = await service.executions(admin, True, page=1, page_size=100, agent_id=agent_a, status="success", trace_id="trace-a", request_id="req-a")
    assert total == 1 and rows[0].id == exec_a

@pytest.mark.asyncio
async def test_owner_cannot_expand_audit_scope_with_filters(db):
    owner_a, _, _, _, agent_b, _, _ = await seed(db)
    service = RuntimeQueryService(db)
    _, _, total, rows = await service.audit_logs(owner_a, False, page=1, page_size=100, agent_id=agent_b)
    assert total == 0 and rows == []

@pytest.mark.asyncio
async def test_pagination_and_filter_combination(db):
    owner_a, _, _, agent_a, _, _, _ = await seed(db)
    service = RuntimeQueryService(db)
    _, page_size, total, rows = await service.executions(owner_a, False, page=1, page_size=10000, status="success", agent_id=agent_a)
    assert page_size == 100 and total == 1 and len(rows) == 1
