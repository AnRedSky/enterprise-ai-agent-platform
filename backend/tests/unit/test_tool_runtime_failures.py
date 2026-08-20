import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.core import Agent, AgentTool, AuditLog, Base, Tool, User
from app.models.execution import Execution
from app.services.tool_audit import AuditLogAdapter
from app.services.tool_observability import ToolObservabilityAdapter
from app.services.tool_rbac import ToolRBACService
from app.services.tool_repository import SqlAlchemyAuditRepository, SqlAlchemyToolRepository
from app.services.tool_runtime_service import ToolExecutionContext, ToolRuntimeService
from app.tools.exceptions import ToolExecutionError


@pytest.mark.asyncio
async def test_runtime_failure_is_persisted_in_audit():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        actor_id, agent_id, tool_id, execution_id = [uuid.uuid4() for _ in range(4)]
        actor = User(id=actor_id, username="failure-owner", password_hash="x")
        agent = Agent(id=agent_id, name="failure-agent", owner_id=actor_id, status="active")
        tool = Tool(id=tool_id, name=f"failure-{uuid.uuid4()}", enabled=True, input_schema={"type": "object"})
        binding = AgentTool(agent_id=agent_id, tool_id=tool_id, enabled=True)
        execution = Execution(id=execution_id, request_id="req-failure", trace_id="trace-failure", agent_id=agent_id, status="running")
        db.add_all([actor, agent, tool, binding, execution])
        await db.flush()

        async def failing_http(_):
            raise ToolExecutionError("TIMEOUT", "timed out")

        import app.services.tool_runtime_service as runtime_module
        original = runtime_module.execute_http_tool
        runtime_module.execute_http_tool = failing_http
        try:
            repo = SqlAlchemyToolRepository(db, Tool, AgentTool)
            audit = AuditLogAdapter(SqlAlchemyAuditRepository(db, AuditLog))
            runtime = ToolRuntimeService(
                repo,
                repo,
                ToolRBACService(db).can_execute,
                audit_logger=audit,
                observability=ToolObservabilityAdapter(db),
            )
            context = ToolExecutionContext(actor_id, agent_id, tool_id, execution_id, "trace-failure", "req-failure")
            with pytest.raises(ToolExecutionError, match="timed out"):
                await runtime.execute(context, {"url": "https://example.test"})
            await db.commit()
        finally:
            runtime_module.execute_http_tool = original

        audit_record = await db.scalar(select(AuditLog).where(AuditLog.execution_id == execution_id))
        assert audit_record is not None
        assert audit_record.status == "failure"
        assert audit_record.error_code == "TIMEOUT"

    await engine.dispose()
