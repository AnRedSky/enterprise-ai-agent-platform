"""Runtime Audit / Trace 关联查询领域服务。"""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.audit import AuditLog
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent


MAX_PAGE_SIZE = 100


class TracePage(TypedDict):
    items: list[WorkflowTraceEvent]
    page: int
    page_size: int
    total: int


class AuditPage(TypedDict):
    items: list[AuditLog]
    page: int
    page_size: int
    total: int


class CorrelationResponse(TypedDict, total=False):
    execution: WorkflowExecution | None
    traces: TracePage
    audits: AuditPage
    operator_actions: list[OperatorActionIdempotency]
    focus_audit_id: UUID | None
    focus_operator_action_id: UUID | None


class RuntimeAuditTraceCorrelationService:
    """提供 tenant-scoped 的 Execution / Trace / Audit / Operator Action 双向关联查询。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _page(page: int, page_size: int) -> tuple[int, int, int]:
        normalized_page = max(page, 1)
        normalized_size = min(max(page_size, 1), MAX_PAGE_SIZE)
        return normalized_page, normalized_size, (normalized_page - 1) * normalized_size

    async def _paged_traces(
        self,
        tenant_id: UUID,
        execution_id: UUID,
        page: int,
        page_size: int,
        *,
        event_type: str | None = None,
        status: str | None = None,
    ) -> TracePage:
        page, page_size, offset = self._page(page, page_size)
        stmt = select(WorkflowTraceEvent).where(
            WorkflowTraceEvent.tenant_id == tenant_id,
            WorkflowTraceEvent.execution_id == execution_id,
        )
        if event_type:
            stmt = stmt.where(WorkflowTraceEvent.event_type == event_type)
        if status:
            stmt = stmt.where(WorkflowTraceEvent.status == status)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (
            await self.db.execute(
                stmt.order_by(WorkflowTraceEvent.created_at.asc(), WorkflowTraceEvent.id.asc())
                .offset(offset)
                .limit(page_size)
            )
        ).scalars().all()
        return {"items": list(rows), "page": page, "page_size": page_size, "total": total}

    async def _paged_audits(
        self,
        tenant_id: UUID,
        execution_id: UUID | None,
        page: int,
        page_size: int,
        *,
        action: str | None = None,
        status: str | None = None,
        operator_action_id: UUID | None = None,
    ) -> AuditPage:
        """按 Execution 或指定 Operator Action 查询正式 Audit 与历史 Trace 恢复 Audit。"""
        page, page_size, offset = self._page(page, page_size)
        execution_audit_scope = None
        if execution_id is not None:
            trace_ids = select(WorkflowTraceEvent.trace_id).where(
                WorkflowTraceEvent.tenant_id == tenant_id,
                WorkflowTraceEvent.execution_id == execution_id,
            )
            execution_audit_scope = or_(
                AuditLog.workflow_execution_id == execution_id,
                (
                    AuditLog.workflow_execution_id.is_(None)
                    & AuditLog.trace_id.in_(trace_ids)
                ),
            )
        if operator_action_id is not None:
            direct_scope = AuditLog.operator_action_id == operator_action_id
            scope = direct_scope if execution_audit_scope is None else or_(execution_audit_scope, direct_scope)
        else:
            scope = execution_audit_scope
        if scope is None:
            return {"items": [], "page": page, "page_size": page_size, "total": 0}
        stmt = select(AuditLog).where(
            AuditLog.tenant_id == tenant_id,
            scope,
        )
        if action:
            formal_audit = aliased(AuditLog)
            matching_formal_action = select(formal_audit.id).where(
                formal_audit.tenant_id == tenant_id,
                formal_audit.workflow_execution_id == execution_id,
                formal_audit.action == action,
            ).exists() if execution_id is not None else None
            action_scope = AuditLog.action == action
            if matching_formal_action is not None:
                action_scope = or_(
                    action_scope,
                    AuditLog.workflow_execution_id.is_(None) & matching_formal_action,
                )
            stmt = stmt.where(action_scope)
        if status:
            stmt = stmt.where(AuditLog.status == status)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (
            await self.db.execute(
                stmt.order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
                .offset(offset)
                .limit(page_size)
            )
        ).scalars().all()
        return {"items": list(rows), "page": page, "page_size": page_size, "total": total}

    async def _operator_actions(self, tenant_id: UUID, execution_id: UUID) -> list[OperatorActionIdempotency]:
        stmt = select(OperatorActionIdempotency).where(
            OperatorActionIdempotency.tenant_id == tenant_id,
            or_(
                (
                    (OperatorActionIdempotency.resource_type == "workflow_execution")
                    & (OperatorActionIdempotency.resource_id == execution_id)
                ),
                (
                    (OperatorActionIdempotency.result_resource_type == "workflow_execution")
                    & (OperatorActionIdempotency.result_resource_id == execution_id)
                ),
            ),
        ).order_by(OperatorActionIdempotency.created_at.asc(), OperatorActionIdempotency.id.asc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def _execution(self, tenant_id: UUID, execution_id: UUID) -> WorkflowExecution | None:
        return (
            await self.db.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.tenant_id == tenant_id,
                    WorkflowExecution.id == execution_id,
                )
            )
        ).scalar_one_or_none()

    async def _execution_ids_from_trace(self, tenant_id: UUID, trace_id: str) -> list[UUID]:
        """解析 Trace ID 对应的唯一 Execution；最多读取两个不同 Execution 以检测歧义。"""
        result = await self.db.execute(
            select(WorkflowTraceEvent.execution_id)
            .where(
                WorkflowTraceEvent.tenant_id == tenant_id,
                WorkflowTraceEvent.trace_id == trace_id,
            )
            .distinct()
            .limit(2)
        )
        return list(result.scalars().all())

    @staticmethod
    def _resolve_unique_execution(execution_ids: list[UUID], trace_id: str) -> UUID | None:
        """只接受唯一 Execution 映射，禁止通过排序或首行猜测关联目标。"""
        if not execution_ids:
            return None
        if len(execution_ids) > 1:
            raise HTTPException(
                status_code=409,
                detail=f"Trace ID maps to multiple Workflow Executions: {trace_id}",
            )
        return execution_ids[0]

    async def _execution_id_from_audit(self, tenant_id: UUID, audit: AuditLog) -> UUID | None:
        if audit.workflow_execution_id is not None:
            return audit.workflow_execution_id
        if not audit.trace_id:
            return None
        execution_ids = await self._execution_ids_from_trace(tenant_id, audit.trace_id)
        return self._resolve_unique_execution(execution_ids, audit.trace_id)

    async def _operator_action(self, tenant_id: UUID, operator_action_id: UUID) -> OperatorActionIdempotency | None:
        return (
            await self.db.execute(
                select(OperatorActionIdempotency).where(
                    OperatorActionIdempotency.tenant_id == tenant_id,
                    OperatorActionIdempotency.id == operator_action_id,
                )
            )
        ).scalar_one_or_none()

    @staticmethod
    def _empty_response(action: OperatorActionIdempotency, page: int, page_size: int, audit_page: int, audit_page_size: int) -> CorrelationResponse:
        return {
            "execution": None,
            "traces": {"items": [], "page": page, "page_size": page_size, "total": 0},
            "audits": {"items": [], "page": audit_page, "page_size": audit_page_size, "total": 0},
            "operator_actions": [action],
            "focus_operator_action_id": action.id,
        }

    async def by_execution(
        self,
        tenant_id: UUID,
        execution_id: UUID,
        *,
        trace_page: int = 1,
        trace_page_size: int = 50,
        audit_page: int = 1,
        audit_page_size: int = 50,
        trace_event_type: str | None = None,
        trace_status: str | None = None,
        audit_action: str | None = None,
        audit_status: str | None = None,
    ) -> CorrelationResponse | None:
        execution = await self._execution(tenant_id, execution_id)
        if execution is None:
            return None
        return {
            "execution": execution,
            "traces": await self._paged_traces(
                tenant_id,
                execution_id,
                trace_page,
                trace_page_size,
                event_type=trace_event_type,
                status=trace_status,
            ),
            "audits": await self._paged_audits(
                tenant_id,
                execution_id,
                audit_page,
                audit_page_size,
                action=audit_action,
                status=audit_status,
            ),
            "operator_actions": await self._operator_actions(tenant_id, execution_id),
        }

    async def by_trace(
        self,
        tenant_id: UUID,
        trace_id: str,
        *,
        trace_page: int = 1,
        trace_page_size: int = 50,
        audit_page: int = 1,
        audit_page_size: int = 50,
        trace_event_type: str | None = None,
        trace_status: str | None = None,
        audit_action: str | None = None,
        audit_status: str | None = None,
    ) -> CorrelationResponse | None:
        execution_ids = await self._execution_ids_from_trace(tenant_id, trace_id)
        execution_id = self._resolve_unique_execution(execution_ids, trace_id)
        if execution_id is None:
            return None
        return await self.by_execution(
            tenant_id,
            execution_id,
            trace_page=trace_page,
            trace_page_size=trace_page_size,
            audit_page=audit_page,
            audit_page_size=audit_page_size,
            trace_event_type=trace_event_type,
            trace_status=trace_status,
            audit_action=audit_action,
            audit_status=audit_status,
        )

    async def by_audit(
        self,
        tenant_id: UUID,
        audit_id: UUID,
        *,
        trace_page: int = 1,
        trace_page_size: int = 50,
        audit_page: int = 1,
        audit_page_size: int = 50,
        trace_event_type: str | None = None,
        trace_status: str | None = None,
        audit_action: str | None = None,
        audit_status: str | None = None,
    ) -> CorrelationResponse | None:
        audit = (
            await self.db.execute(
                select(AuditLog).where(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.id == audit_id,
                )
            )
        ).scalar_one_or_none()
        if audit is None:
            return None
        execution_id = await self._execution_id_from_audit(tenant_id, audit)
        if execution_id is None and audit.operator_action_id is not None:
            action = await self._operator_action(tenant_id, audit.operator_action_id)
            if action is None:
                return None
            page, page_size, _ = self._page(trace_page, trace_page_size)
            return {
                "execution": None,
                "traces": {"items": [], "page": page, "page_size": page_size, "total": 0},
                "audits": await self._paged_audits(
                    tenant_id, None, audit_page, audit_page_size,
                    action=audit_action, status=audit_status,
                    operator_action_id=action.id,
                ),
                "operator_actions": [action],
                "focus_audit_id": audit.id,
                "focus_operator_action_id": action.id,
            }
        if execution_id is None:
            return None
        result = await self.by_execution(
            tenant_id,
            execution_id,
            trace_page=trace_page,
            trace_page_size=trace_page_size,
            audit_page=audit_page,
            audit_page_size=audit_page_size,
            trace_event_type=trace_event_type,
            trace_status=trace_status,
            audit_action=audit_action,
            audit_status=audit_status,
        )
        if result is not None:
            result["focus_audit_id"] = audit.id
            result["focus_operator_action_id"] = audit.operator_action_id
        return result

    async def by_operator_action(
        self,
        tenant_id: UUID,
        operator_action_id: UUID,
        *,
        trace_page: int = 1,
        trace_page_size: int = 50,
        audit_page: int = 1,
        audit_page_size: int = 50,
        trace_event_type: str | None = None,
        trace_status: str | None = None,
        audit_action: str | None = None,
        audit_status: str | None = None,
    ) -> CorrelationResponse | None:
        action = await self._operator_action(tenant_id, operator_action_id)
        if action is None:
            return None
        execution_id = (
            action.result_resource_id
            if action.result_resource_type == "workflow_execution"
            else action.resource_id if action.resource_type == "workflow_execution" else None
        )
        if execution_id is None:
            trace_page_number, trace_page_size_normalized, _ = self._page(trace_page, trace_page_size)
            audit_page_number, audit_page_size_normalized, _ = self._page(audit_page, audit_page_size)
            return {
                "execution": None,
                "traces": {"items": [], "page": trace_page_number, "page_size": trace_page_size_normalized, "total": 0},
                "audits": await self._paged_audits(
                    tenant_id, None, audit_page, audit_page_size,
                    action=audit_action, status=audit_status,
                    operator_action_id=action.id,
                ),
                "operator_actions": [action],
                "focus_operator_action_id": action.id,
            }
        result = await self.by_execution(
            tenant_id,
            execution_id,
            trace_page=trace_page,
            trace_page_size=trace_page_size,
            audit_page=audit_page,
            audit_page_size=audit_page_size,
            trace_event_type=trace_event_type,
            trace_status=trace_status,
            audit_action=audit_action,
            audit_status=audit_status,
        )
        if result is None:
            return None
        # Operator Action 反查只返回与当前幂等事实直接关联的 Audit；Execution 级生命周期 Audit
        # 仍由 by_execution 保持完整查询语义，避免两种查询入口混淆聚合层级。
        result["audits"] = await self._paged_audits(
            tenant_id,
            None,
            audit_page,
            audit_page_size,
            action=audit_action,
            status=audit_status,
            operator_action_id=action.id,
        )
        result["focus_operator_action_id"] = action.id
        return result
