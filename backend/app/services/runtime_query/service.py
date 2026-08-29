from datetime import datetime, UTC
from typing import Any
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
    """提供 Runtime 与 Integration Event 运维查询。

    职责：统一处理分页、过滤、权限范围以及租户边界。
    边界：只负责查询，不负责事件写入、投递编排或数据库事务提交。
    关键依赖：SQLAlchemy AsyncSession 与 Runtime/Integration 领域模型。
    """

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

    def _integration_event_filters(self, stmt, *, event_type=None, source=None, status=None,
                                   subject=None, trace_id=None, request_id=None,
                                   occurred_from=None, occurred_to=None):
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
        if occurred_from:
            stmt = stmt.where(IntegrationEventRecord.occurred_at >= occurred_from)
        if occurred_to:
            stmt = stmt.where(IntegrationEventRecord.occurred_at <= occurred_to)
        return stmt

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
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ):
        """查询 Durable Integration Event 运维视图。

        Args:
            tenant_id: 当前认证上下文中的租户标识，作为强制隔离边界。
            page: 从 1 开始的页码。
            page_size: 单页数量，最大值由服务统一限制。
            event_type: 可选事件类型过滤。
            source: 可选事件来源过滤。
            status: 可选事件状态过滤。
            subject: 可选业务主体过滤。
            trace_id: 可选链路标识过滤。
            request_id: 可选请求标识过滤。
            occurred_from: 可选事件发生时间下界。
            occurred_to: 可选事件发生时间上界。

        Returns:
            `(page, page_size, total, rows)`，其中 rows 只包含当前 tenant 的事件。
        """
        page, page_size, offset = self._page(page, page_size)
        stmt = select(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id == tenant_id)
        stmt = self._integration_event_filters(
            stmt,
            event_type=event_type,
            source=source,
            status=status,
            subject=subject,
            trace_id=trace_id,
            request_id=request_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (await self.db.execute(
            stmt.order_by(IntegrationEventRecord.occurred_at.desc(), IntegrationEventRecord.id.desc())
            .offset(offset).limit(page_size)
        )).scalars().all()
        return page, page_size, total, rows

    async def integration_event_summary(
        self,
        tenant_id: UUID,
        *,
        event_type: str | None = None,
        source: str | None = None,
        status: str | None = None,
        subject: str | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> dict[str, Any]:
        """生成当前租户 Integration Event 的运维聚合摘要。

        Args:
            tenant_id: 当前认证上下文中的租户标识，不允许由客户端自由指定。
            event_type: 与列表查询一致的事件类型过滤。
            source: 与列表查询一致的事件来源过滤。
            status: 与列表查询一致的状态过滤。
            subject: 与列表查询一致的业务主体过滤。
            trace_id: 与列表查询一致的链路标识过滤。
            request_id: 与列表查询一致的请求标识过滤。
            occurred_from: 事件发生时间下界。
            occurred_to: 事件发生时间上界。

        Returns:
            包含总数、状态计数、来源计数和生成时间的摘要。
        """
        base = select(IntegrationEventRecord).where(IntegrationEventRecord.tenant_id == tenant_id)
        base = self._integration_event_filters(
            base,
            event_type=event_type,
            source=source,
            status=status,
            subject=subject,
            trace_id=trace_id,
            request_id=request_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        ).subquery()
        total = (await self.db.execute(select(func.count()).select_from(base))).scalar_one()
        status_rows = await self.db.execute(select(base.c.status, func.count()).group_by(base.c.status))
        source_rows = await self.db.execute(select(base.c.source, func.count()).group_by(base.c.source))
        return {
            "total": total,
            "status_counts": {key: value for key, value in status_rows.all()},
            "source_counts": {key: value for key, value in source_rows.all()},
            "generated_at": datetime.now(UTC),
        }
