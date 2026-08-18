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
    actor = User(username="owner", password_hash="x")
    agent = Agent(name="runtime-agent", owner_id=actor.id, status="active")
    tool = Tool(name=f"http-{uuid.uuid4()}", endpoint="https://example.test", enabled=True, input_schema={"type": "object"})
    binding = AgentTool(agent_id=agent.id, tool_id=tool.id, enabled=True)
    execution = Execution(
        request_id="req-e2e",
        trace_id="trace-e2e",
        agent_id=agent.id,
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
        actor_id=actor.id,
        agent_id=agent.id,
        tool_id=tool.id,
        execution_id=execution.id,
        trace_id=execution.trace_id,
        request_id=execution.request_id,
    )

    result = await service.execute(
        context,
        {"url": "https://example.test", "headers": {"Authorization": "secret"}},
    )
    await db_session.commit()

    assert result["status_code"] == 200
    audit = await db_session.scalar(select(AuditLog).where(AuditLog.execution_id == execution.id))
    assert audit is not None
    assert audit.status == "success"

    event = await db_session.scalar(
        select(ExecutionEvent).where(
            ExecutionEvent.execution_id == execution.id,
            ExecutionEvent.tool_id == tool.id,
        )
    )
    assert event is not None
    assert event.span_type == "tool"
    assert event.status == "completed"


@pytest.mark.asyncio
async def test_tool_runtime_denies_non_owner(db_session):
    owner = User(username="owner2", password_hash="x")
    actor = User(username="actor2", password_hash="x")
    agent = Agent(name="restricted-agent", owner_id=owner.id, status="active")
    tool = Tool(name=f"restricted-{uuid.uuid4()}", enabled=True, input_schema={"type": "object"})
    binding = AgentTool(agent_id=agent.id, tool_id=tool.id, enabled=True)
    db_session.add_all([owner, actor, agent, tool, binding])
    await db_session.flush()

    allowed = await ToolRBACService(db_session).can_execute(actor.id, agent.id, tool.id)
    assert allowed is False
