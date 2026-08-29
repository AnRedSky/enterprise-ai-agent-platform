"""Runtime 查询服务模块。

职责：提供执行、事件、审计日志、Workflow Trace 与 Durable Integration Event 的分页查询、过滤与权限范围控制。
边界：只负责查询业务规则与访问范围，不负责执行编排、审计写入或数据库 Session 创建。
关键依赖：SQLAlchemy AsyncSession，以及 Runtime/Integration 领域模型。
"""

from uuid import UUID

from sqlalchemy import Select, cast, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.core import Agent
from app.models.execution import Execution, ExecutionEvent
from app.models.integration_event import IntegrationEventRecord
from app.models.model_provider import ModelProfile, ModelProvider
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
            model_provider_ids = select(cast(ModelProvider.id, String)).join(
                OrganizationMembership,
                OrganizationMembership.organization_id == ModelProvider.organization_id,
            ).where(
                OrganizationMembership.user_id == actor_id,
                OrganizationMembership.status == "active",
            )
            model_profile_ids = select(cast(ModelProfile.id, String)).join(
                ModelProvider,
                ModelProvider.id == ModelProfile.provider_id,
            ).join(
                OrganizationMembership,
                OrganizationMembership.organization_id == ModelProvider.organization_id,
            ).where(
                OrganizationMembership.user_id == actor_id,
                OrganizationMembership.status == "active",
            )
            stmt = stmt.outerjoin(Agent, Agent.id == AuditLog.agent_id).outerjoin(Workflow, Workflow.id == AuditLog.workflow_id)
            stmt = stmt.where(or_(
                Agent.owner_id == actor_id,
                Workflow.owner_id == actor_id,
                (AuditLog.resource_type == "organization") & AuditLog.resource_id.in_(organization_ids),
                (AuditLog.resource_type == "organization_membership") & AuditLog.resource_id.in_(membership_ids),
                (AuditLog.resource_type == "model_provider") & AuditLog.resource_id.in_(model_provider_ids),
                (AuditLog.resource_type == "model_profile") & AuditLog.resource_id.in_(model_profile_ids),
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

    async def integration_events(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        event_type: str | None = None,
        source: str | None = None,
        status: str | None = None,
        subject: str | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
    ):
        """查询 Durable Integration Event 运维视图；tenant_id 是强制隔离边界。"""
        page, page_size, offset = self._page(page, page_size)
        stmt = select(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id == tenant_id)
        if event_type:
            stmt = stmt.where(IntegrationEventRecord.event_type == event_type)
        if source:
            stmt = stmt.where(IntegrationEventRecord.source == source)
        if status:
            stmt = stmt.where(IntegrationEventRecord.status == status)
        if subject:
            stmt = stmt.where(IntegrationEventRecord.subject == subject)
        if trace_id:
            stmt = stmt.where(IntegrationEventRecord.trace_id == trace_id)
        if request_id:
            stmt = stmt.where(IntegrationEventRecord.request_id == request_id)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (await self.db.execute(
            stmt.order_by(IntegrationEventRecord.created_at.desc(), IntegrationEventRecord.id.desc())
            .offset(offset).limit(page_size)
        )).scalars().all()
        return page, page_size, total, rows
