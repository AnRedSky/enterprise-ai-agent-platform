import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.core import Agent, AgentTool, AuditLog, Base, Tool, User
from app.models.execution import Execution, ExecutionEvent
from app.services.tool_audit import AuditLogAdapter
from app.services.tool_observability import ToolObservabilityAdapter
from app.services.tool_rbac import ToolRBACService
from app.services.tool_repository import SqlAlchemyAuditRepository, SqlAlchemyToolRepository
from app.services.tool_runtime_service import ToolExecutionContext, ToolRuntimeService


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_tool_runtime_persists_audit_and_observability(db_session, monkeypatch):
    actor_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    actor = User(id=actor_id, username="owner", password_hash="x")
    agent = Agent(id=agent_id, name="runtime-agent", owner_id=actor_id, status="active")
    tool = Tool(id=tool_id, name=f"http-{uuid.uuid4()}", endpoint="https://example.test", enabled=True, input_schema={"type": "object"})
    binding = AgentTool(agent_id=agent_id, tool_id=tool_id, enabled=True)
    execution = Execution(
        id=execution_id,
        request_id="req-e2e",
        trace_id="trace-e2e",
        agent_id=agent_id,
        status="running",
    )
    db_session.add_all([actor, agent, tool, binding, execution])
    await db_session.flush()

    async def fake_http(arguments):
        return {"status_code": 200, "body": "ok", "headers": {}}

    monkeypatch.setattr("app.services.tool_runtime_service.execute_http_tool", fake_http)

    tool_repo = SqlAlchemyToolRepository(db_session, Tool, AgentTool)
    audit_repo = SqlAlchemyAuditRepository(db_session, AuditLog)
    service = ToolRuntimeService(
        tool_repo,
        tool_repo,
        ToolRBACService(db_session).can_execute,
        audit_logger=AuditLogAdapter(audit_repo),
        observability=ToolObservabilityAdapter(db_session),
    )
    context = ToolExecutionContext(
        actor_id=actor_id,
        agent_id=agent_id,
        tool_id=tool_id,
        execution_id=execution_id,
        trace_id=execution.trace_id,
        request_id=execution.request_id,
    )

    result = await service.execute(
        context,
        {"url": "https://example.test", "headers": {"Authorization": "secret"}},
    )
    await db_session.commit()

    assert result["status_code"] == 200
    audit = await db_session.scalar(select(AuditLog).where(AuditLog.execution_id == execution_id))
    assert audit is not None
    assert audit.status == "success"

    event = await db_session.scalar(
        select(ExecutionEvent).where(
            ExecutionEvent.execution_id == execution_id,
            ExecutionEvent.tool_id == tool_id,
        )
    )
    assert event is not None
    assert event.span_type == "tool"
    assert event.status == "completed"


@pytest.mark.asyncio
async def test_tool_runtime_denies_non_owner(db_session):
    owner_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    owner = User(id=owner_id, username="owner2", password_hash="x")
    actor = User(id=actor_id, username="actor2", password_hash="x")
    agent = Agent(id=agent_id, name="restricted-agent", owner_id=owner_id, status="active")
    tool = Tool(id=tool_id, name=f"restricted-{uuid.uuid4()}", enabled=True, input_schema={"type": "object"})
    binding = AgentTool(agent_id=agent_id, tool_id=tool_id, enabled=True)
    db_session.add_all([owner, actor, agent, tool, binding])
    await db_session.flush()

    allowed = await ToolRBACService(db_session).can_execute(actor_id, agent_id, tool_id)
    assert allowed is False
