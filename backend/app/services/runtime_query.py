from uuid import UUID
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.models.core import Agent
from app.models.execution import Execution, ExecutionEvent

MAX_PAGE_SIZE = 100

class RuntimeQueryService:
    def __init__(self, db: AsyncSession): self.db = db

    @staticmethod
    def _page(page: int, page_size: int):
        page = max(page, 1); page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
        return page, page_size, (page - 1) * page_size

    def _agent_scope(self, stmt, actor_id: UUID, is_admin: bool):
        if not is_admin:
            stmt = stmt.join(Agent, Agent.id == Execution.agent_id).where(Agent.owner_id == actor_id)
        return stmt

    async def executions(self, actor_id: UUID, is_admin: bool, page=1, page_size=20, status=None, agent_id=None, trace_id=None, request_id=None, session_id=None, started_from=None, started_to=None):
        page, page_size, offset = self._page(page, page_size)
        stmt: Select = self._agent_scope(select(Execution), actor_id, is_admin)
        if agent_id: stmt = stmt.where(Execution.agent_id == agent_id)
        if status: stmt = stmt.where(Execution.status == status)
        if trace_id: stmt = stmt.where(Execution.trace_id == trace_id)
        if request_id: stmt = stmt.where(Execution.request_id == request_id)
        if session_id: stmt = stmt.where(Execution.session_id == session_id)
        if started_from: stmt = stmt.where(Execution.started_at >= started_from)
        if started_to: stmt = stmt.where(Execution.started_at <= started_to)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (await self.db.execute(stmt.order_by(Execution.started_at.desc()).offset(offset).limit(page_size))).scalars().all()
        return page, page_size, total, rows

    async def execution(self, actor_id: UUID, is_admin: bool, execution_id: UUID):
        stmt = self._agent_scope(select(Execution).where(Execution.id == execution_id), actor_id, is_admin)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def events(self, actor_id: UUID, is_admin: bool, execution_id: UUID):
        execution = await self.execution(actor_id, is_admin, execution_id)
        if execution is None: return None, []
        rows = (await self.db.execute(select(ExecutionEvent).where(ExecutionEvent.execution_id == execution_id).order_by(ExecutionEvent.created_at.asc()))).scalars().all()
        return execution, rows

    async def audit_logs(self, actor_id: UUID, is_admin: bool, page=1, page_size=20, agent_id=None, tool_id=None, status=None):
        page, page_size, offset = self._page(page, page_size)
        stmt = select(AuditLog)
        if not is_admin: stmt = stmt.join(Agent, Agent.id == AuditLog.agent_id).where(Agent.owner_id == actor_id)
        if agent_id: stmt = stmt.where(AuditLog.agent_id == agent_id)
        if tool_id: stmt = stmt.where(AuditLog.tool_id == tool_id)
        if status: stmt = stmt.where(AuditLog.status == status)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (await self.db.execute(stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size))).scalars().all()
        return page, page_size, total, rows
