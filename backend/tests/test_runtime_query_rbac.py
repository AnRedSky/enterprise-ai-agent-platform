from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.core import Agent, AuditLog, Base
from app.models.execution import Execution, ExecutionEvent
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
    execution_a, execution_b = uuid4(), uuid4()
    session.add_all([
        Agent(id=agent_a, name="a", owner_id=owner_a),
        Agent(id=agent_b, name="b", owner_id=owner_b),
        Execution(id=execution_a, request_id="req-a", trace_id="trace-a", agent_id=agent_a, status="success", started_at=datetime.now(datetime.UTC)),
        Execution(id=execution_b, request_id="req-b", trace_id="trace-b", agent_id=agent_b, status="failed", started_at=datetime.now(datetime.UTC)),
        ExecutionEvent(id=uuid4(), execution_id=execution_a, trace_id="trace-a", span_type="model", status="completed"),
        ExecutionEvent(id=uuid4(), execution_id=execution_b, trace_id="trace-b", span_type="tool", status="completed"),
        AuditLog(id=uuid4(), actor_id=owner_a, agent_id=agent_a, action="run", status="success"),
        AuditLog(id=uuid4(), actor_id=owner_b, agent_id=agent_b, action="run", status="failed"),
    ])
    await session.commit()
    return owner_a, owner_b, admin, agent_a, agent_b, execution_a, execution_b


@pytest.mark.asyncio
async def test_owner_cannot_see_other_execution_or_events(db):
    owner_a, _, _, _, _, execution_a, execution_b = await seed(db)
    service = RuntimeQueryService(db)
    _, _, total, rows = await service.executions(owner_a, False, page=1, page_size=100)
    assert total == 1 and [row.id for row in rows] == [execution_a]
    assert await service.execution(owner_a, False, execution_b) is None
    execution, events = await service.events(owner_a, False, execution_b)
    assert execution is None and events == []


@pytest.mark.asyncio
async def test_admin_can_see_all_and_filters_apply(db):
    _, _, admin, agent_a, _, execution_a, _ = await seed(db)
    service = RuntimeQueryService(db)
    _, _, total, rows = await service.executions(
        admin,
        True,
        page=1,
        page_size=100,
        status="success",
        agent_id=agent_a,
        trace_id="trace-a",
        request_id="req-a",
    )
    assert total == 1 and rows[0].id == execution_a


@pytest.mark.asyncio
async def test_owner_audit_scope_and_filters_are_isolated(db):
    owner_a, _, _, agent_a, agent_b, _, _ = await seed(db)
    service = RuntimeQueryService(db)
    _, _, total, rows = await service.audit_logs(owner_a, False, page=1, page_size=100)
    assert total == 1 and rows[0].agent_id == agent_a
    _, _, total, rows = await service.audit_logs(owner_a, False, page=1, page_size=100, agent_id=agent_b)
    assert total == 0 and rows == []


@pytest.mark.asyncio
async def test_pagination_is_capped(db):
    owner_a, _, _, _, _, _, _ = await seed(db)
    service = RuntimeQueryService(db)
    _, page_size, _, _ = await service.executions(owner_a, False, page=1, page_size=10000)
    assert page_size == 100


@pytest.mark.asyncio
async def test_execution_pagination_is_deterministic_when_timestamps_tie(db):
    owner_a = uuid4()
    agent_a = uuid4()
    timestamp = datetime.now(datetime.UTC)
    execution_low = uuid4()
    execution_high = uuid4()
    if execution_low > execution_high:
        execution_low, execution_high = execution_high, execution_low

    db.add(Agent(id=agent_a, name="tie-agent", owner_id=owner_a))
    db.add_all([
        Execution(id=execution_low, request_id="tie-low", trace_id="tie", agent_id=agent_a, status="success", started_at=timestamp),
        Execution(id=execution_high, request_id="tie-high", trace_id="tie", agent_id=agent_a, status="success", started_at=timestamp),
    ])
    await db.commit()

    service = RuntimeQueryService(db)
    _, _, total, page_one = await service.executions(owner_a, False, page=1, page_size=1)
    _, _, _, page_two = await service.executions(owner_a, False, page=2, page_size=1)

    assert total == 2
    assert page_one[0].id == execution_high
    assert page_two[0].id == execution_low
