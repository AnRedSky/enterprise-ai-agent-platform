"""Runtime Audit / Trace 关联查询领域服务。

职责：把 Workflow Execution、Workflow Trace、AuditLog 与 Operator Action 幂等事实组成统一只读关联视图。
边界：不创建或修改任何运行态事实，不复制 Workflow / Trigger 生命周期规则；所有租户范围由调用方认证上下文传入。
关键依赖：WorkflowExecution、WorkflowTraceEvent、AuditLog、OperatorActionIdempotency 与 SQLAlchemy AsyncSession。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.operator_action import OperatorActionIdempotency
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent


MAX_PAGE_SIZE = 100


class RuntimeAuditTraceCorrelationService:
    """提供 tenant-scoped 的 Execution / Trace / Audit / Operator Action 双向关联查询。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _page(page: int, page_size: int) -> tuple[int, int, int]:
        """规范分页参数并计算稳定 offset。"""
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
    ) -> dict:
        """查询 Execution 的 Trace 事件并使用 created_at + id 保证稳定排序。"""
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
        rows = (await self.db.execute(
            stmt.order_by(WorkflowTraceEvent.created_at.asc(), WorkflowTraceEvent.id.asc())
            .offset(offset).limit(page_size)
        )).scalars().all()
        return {"items": list(rows), "page": page, "page_size": page_size, "total": total}

    async def _paged_audits(
        self,
        tenant_id: UUID,
        execution_id: UUID,
        page: int,
        page_size: int,
        *,
        action: str | None = None,
        status: str | None = None,
    ) -> dict:
        """查询 Execution 的 AuditLog，并以 created_at + id 保证稳定排序。"""
        page, page_size, offset = self._page(page, page_size)
        stmt = select(AuditLog).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.workflow_execution_id == execution_id,
        )
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if status:
            stmt = stmt.where(AuditLog.status == status)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (await self.db.execute(
            stmt.order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
            .offset(offset).limit(page_size)
        )).scalars().all()
        return {"items": list(rows), "page": page, "page_size": page_size, "total": total}

    async def _operator_actions(self, tenant_id: UUID, execution_id: UUID) -> list[OperatorActionIdempotency]:
        """查询直接操作 Execution 或产生该 Execution 结果的 Operator Action。"""
        stmt = select(OperatorActionIdempotency).where(
            OperatorActionIdempotency.tenant_id == tenant_id,
            (
                (OperatorActionIdempotency.resource_type == "workflow_execution")
                & (OperatorActionIdempotency.resource_id == execution_id)
            )
            | (
                (OperatorActionIdempotency.result_resource_type == "workflow_execution")
                & (OperatorActionIdempotency.result_resource_id == execution_id)
            ),
        ).order_by(OperatorActionIdempotency.created_at.asc(), OperatorActionIdempotency.id.asc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def _execution(self, tenant_id: UUID, execution_id: UUID) -> WorkflowExecution | None:
        """按 tenant + execution_id 获取 Workflow Execution，阻断跨租户深链访问。"""
        return (await self.db.execute(select(WorkflowExecution).where(
            WorkflowExecution.tenant_id == tenant_id,
            WorkflowExecution.id == execution_id,
        ))).scalar_one_or_none()

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
    ) -> dict | None:
        """从 Execution 深入 Trace / Audit / Operator Action，并提供稳定分页与筛选。"""
        execution = await self._execution(tenant_id, execution_id)
        if execution is None:
            return None
        return {
            "execution": execution,
            "traces": await self._paged_traces(
                tenant_id, execution_id, trace_page, trace_page_size,
                event_type=trace_event_type, status=trace_status,
            ),
            "audits": await self._paged_audits(
                tenant_id, execution_id, audit_page, audit_page_size,
                action=audit_action, status=audit_status,
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
    ) -> dict | None:
        """从 Trace ID 反向定位 Execution，并返回同一 Execution 的 Audit / Operator Action。"""
        trace = (await self.db.execute(select(WorkflowTraceEvent).where(
            WorkflowTraceEvent.tenant_id == tenant_id,
            WorkflowTraceEvent.trace_id == trace_id,
        ).order_by(WorkflowTraceEvent.created_at.asc(), WorkflowTraceEvent.id.asc()).limit(1))).scalar_one_or_none()
        if trace is None:
            return None
        return await self.by_execution(
            tenant_id,
            trace.execution_id,
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
    ) -> dict | None:
        """从 Audit ID 反向定位 Execution，并返回关联 Trace 与 Operator Action。"""
        audit = (await self.db.execute(select(AuditLog).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.id == audit_id,
        ))).scalar_one_or_none()
        if audit is None or audit.workflow_execution_id is None:
            return None
        result = await self.by_execution(
            tenant_id,
            audit.workflow_execution_id,
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
    ) -> dict | None:
        """从 Operator Action 幂等事实反向定位结果 Execution、Audit 与 Trace。"""
        action = (await self.db.execute(select(OperatorActionIdempotency).where(
            OperatorActionIdempotency.tenant_id == tenant_id,
            OperatorActionIdempotency.id == operator_action_id,
        ))).scalar_one_or_none()
        if action is None:
            return None
        execution_id = (
            action.result_resource_id
            if action.result_resource_type == "workflow_execution"
            else (
                action.resource_id
                if action.resource_type == "workflow_execution"
                else None
            )
        )
        if execution_id is None:
            return {"execution": None, "traces": {"items": [], "page": 1, "page_size": 0, "total": 0},
                    "audits": {"items": [], "page": 1, "page_size": 0, "total": 0},
                    "operator_actions": [action], "focus_operator_action_id": action.id}
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
        result["focus_operator_action_id"] = action.id
        return result
