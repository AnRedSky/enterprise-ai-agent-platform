"""Runtime Operator Action 审计查询服务。

职责：从唯一的 AuditLog 合规事实源中查询 Operator Action 审计记录，并提供租户隔离、分页和精确过滤。
边界：只读查询，不创建第二套审计事实，不执行任何 Operator Action，也不修改 Runtime 状态。
关键依赖：AuditLog、SQLAlchemy AsyncSession。
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


MAX_PAGE_SIZE = 100
OPERATOR_ACTION_PREFIX = "operator."


class OperatorAuditPage(TypedDict):
    """Operator Action 审计分页结果。"""

    items: list[AuditLog]
    page: int
    page_size: int
    total: int


class OperatorAuditQueryService:
    """提供基于 AuditLog 唯一事实源的租户级 Operator Action 审计查询。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _page(page: int, page_size: int) -> tuple[int, int, int]:
        """规范化分页参数。

        Args:
            page: 从 1 开始的页码。
            page_size: 单页数量，最大 100。

        Returns:
            规范化后的页码、页大小和偏移量。
        """
        normalized_page = max(page, 1)
        normalized_size = min(max(page_size, 1), MAX_PAGE_SIZE)
        return normalized_page, normalized_size, (normalized_page - 1) * normalized_size

    async def query(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        action: str | None = None,
        operator_action_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        actor_id: UUID | None = None,
        status: str | None = None,
        workflow_execution_id: UUID | None = None,
        trace_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> OperatorAuditPage:
        """查询当前租户的 Operator Action 审计事实。

        Args:
            tenant_id: 认证上下文确定的租户标识，不接受客户端替代值。
            page: 从 1 开始的页码。
            page_size: 单页数量，统一限制在 1 到 100。
            action: 可选 Operator Action 完整动作名精确匹配，例如 `operator.workflow_execution.retry`。
            operator_action_id: 可选 Operator Action 持久事实标识，用于直接定位 AuditLog 治理关联。
            resource_type: 可选资源类型精确匹配。
            resource_id: 可选资源标识精确匹配。
            actor_id: 可选操作人 UUID 精确匹配。
            status: 可选审计结果精确匹配。
            workflow_execution_id: 可选关联 Workflow Execution 精确匹配。
            trace_id: 可选 Trace ID 精确匹配。
            since: 可选创建时间下界。
            until: 可选创建时间上界。

        Returns:
            只包含当前租户 Operator Action 审计事实的稳定分页结果。

        Raises:
            ValueError: 当 since 晚于 until 时抛出。

        设计意图：Operator Action 的合规事实已经由 OperatorActionGovernanceService 写入 AuditLog；本服务只建立查询入口，避免 RuntimeOperationAudit 与 AuditLog 形成第二套 Operator Action 事实源。operator_action_id 是正式治理关联键，允许管理端直接从 Operator Action 事实定位审计记录。
        """
        if since is not None and until is not None and since > until:
            raise ValueError("since must not be later than until")
        if action is not None and not action.startswith(OPERATOR_ACTION_PREFIX):
            raise ValueError("action must start with operator.")

        page, page_size, offset = self._page(page, page_size)
        stmt = select(AuditLog).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.action.like(f"{OPERATOR_ACTION_PREFIX}%"),
        )
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if operator_action_id is not None:
            stmt = stmt.where(AuditLog.operator_action_id == operator_action_id)
        if resource_type is not None:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if resource_id is not None:
            stmt = stmt.where(AuditLog.resource_id == resource_id)
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if status is not None:
            stmt = stmt.where(AuditLog.status == status)
        if workflow_execution_id is not None:
            stmt = stmt.where(AuditLog.workflow_execution_id == workflow_execution_id)
        if trace_id is not None:
            stmt = stmt.where(AuditLog.trace_id == trace_id)
        if since is not None:
            stmt = stmt.where(AuditLog.created_at >= since)
        if until is not None:
            stmt = stmt.where(AuditLog.created_at <= until)

        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = (
            await self.db.execute(
                stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                .offset(offset)
                .limit(page_size)
            )
        ).scalars().all()
        return {"items": list(rows), "page": page, "page_size": page_size, "total": total}
