from uuid import UUID

from sqlalchemy import Select, cast, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.core import Agent
from app.models.execution import Execution, ExecutionEvent
from app.models.organization import Organization, OrganizationMembership
from app.models.workflow import Workflow
from app.models.workflow_trace import WorkflowTraceEvent

MAX_PAGE_SIZE = 100


class RuntimeQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _page(page: int, page_size: int):
        page = max(page, 1)
        page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
        return page, page_size, (page - 1) * page_size

    def _agent_scope(self, stmt, actor_id: UUID, is_admin: bool):
        if not is_admin:
            stmt = stmt.join(Agent, Agent.id == Execution.agent_id).where(Agent.owner_id == actor_id)
        return stmt

    async def executions(self, actor_id: UUID, is_admin: bool, page=1, page_size=20, status=None,
                         agent_id=None, trace_id=None, request_id=None, session_id=None,
                         started_from=None, started_to=None):
        page, page_size, offset = self._page(page, page_size)
        stmt: Select = self._agent_scope(select(Execution), actor_id, is_admin)
        if agent_id:
            stmt = stmt.where(Execution.agent_id == agent_id)
        if status:
            stmt = stmt.where(Execution.status == status)
        if trace_id:
            stmt = stmt.where(Execution.trace_id == trace_id)
        if request_id:
            stmt = stmt.where(Execution.request_id == request_id)
        if session_id:
            stmt = stmt.where(Execution.session_id == session_id)
        if started_from:
            stmt = stmt.where(Execution.started_at >= started_from)
        if started_to:
            stmt = stmt.where(Execution.started_at <= started_to)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (await self.db.execute(stmt.order_by(Execution.started_at.desc(), Execution.id.desc()).offset(offset).limit(page_size))).scalars().all()
        return page, page_size, total, rows

    async def execution(self, actor_id: UUID, is_admin: bool, execution_id: UUID):
        stmt = self._agent_scope(select(Execution).where(Execution.id == execution_id), actor_id, is_admin)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def events(self, actor_id: UUID, is_admin: bool, execution_id: UUID):
        execution = await self.execution(actor_id, is_admin, execution_id)
        if execution is None:
            return None, []
        rows = (await self.db.execute(select(ExecutionEvent).where(ExecutionEvent.execution_id == execution_id)
                                      .order_by(ExecutionEvent.created_at.asc(), ExecutionEvent.id.asc()))).scalars().all()
        return execution, rows

    async def audit_logs(self, actor_id: UUID, is_admin: bool, page=1, page_size=20,
                         agent_id=None, tool_id=None, status=None, workflow_id=None, workflow_execution_id=None):
        page, page_size, offset = self._page(page, page_size)
        stmt = select(AuditLog)
        if not is_admin:
            # Runtime audit visibility historically followed the actor's Agent/Workflow
            # ownership. Organization governance audit records are scoped differently:
            # their resource ids point to an Organization or Membership, so an active
            # organization member must be able to see mutations for organizations they
            # can access without exposing another organization's audit trail.
            # AuditLog.resource_id is persisted as VARCHAR, therefore UUID subqueries
            # must be cast to String before comparison on PostgreSQL.
            organization_ids = select(cast(Organization.id, String)).join(
                OrganizationMembership,
                OrganizationMembership.organization_id == Organization.id,
            ).where(
                OrganizationMembership.user_id == actor_id,
                OrganizationMembership.status == "active",
            )
            membership_ids = select(cast(OrganizationMembership.id, String)).where(
                OrganizationMembership.user_id == actor_id,
                OrganizationMembership.status == "active",
            )
            stmt = stmt.outerjoin(Agent, Agent.id == AuditLog.agent_id).outerjoin(Workflow, Workflow.id == AuditLog.workflow_id)
            stmt = stmt.where(or_(
                Agent.owner_id == actor_id,
                Workflow.owner_id == actor_id,
                (
                    AuditLog.resource_type == "organization"
                ) & AuditLog.resource_id.in_(organization_ids),
                (
                    AuditLog.resource_type == "organization_membership"
                ) & AuditLog.resource_id.in_(membership_ids),
            ))
        if agent_id:
            stmt = stmt.where(AuditLog.agent_id == agent_id)
        if tool_id:
            stmt = stmt.where(AuditLog.tool_id == tool_id)
        if workflow_id:
            stmt = stmt.where(AuditLog.workflow_id == workflow_id)
        if workflow_execution_id:
            stmt = stmt.where(AuditLog.workflow_execution_id == workflow_execution_id)
        if status:
            stmt = stmt.where(AuditLog.status == status)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (await self.db.execute(stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(page_size))).scalars().all()
        return page, page_size, total, rows

    async def workflow_trace(self, actor_id: UUID, is_admin: bool, execution_id: UUID, tenant_id: UUID):
        stmt = select(WorkflowTraceEvent).where(
            WorkflowTraceEvent.execution_id == execution_id,
            WorkflowTraceEvent.tenant_id == tenant_id,
        )
        if not is_admin:
            stmt = stmt.join(Workflow, Workflow.id == WorkflowTraceEvent.workflow_id).where(Workflow.owner_id == actor_id)
        rows = (await self.db.execute(stmt.order_by(WorkflowTraceEvent.created_at.asc(), WorkflowTraceEvent.id.asc()))).scalars().all()
        return rows
