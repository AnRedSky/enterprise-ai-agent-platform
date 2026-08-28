"""Agent Delegation Repository。

职责：封装 Delegation 的 tenant-scoped 查询、幂等查找与活动数量统计。
边界：不决定预算、权限或状态迁移规则；这些规则由 Delegation Service 统一处理。
关键依赖：SQLAlchemy AsyncSession、AgentDelegation ORM。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_delegation import AgentDelegation


class AgentDelegationRepository:
    """Agent Delegation 数据访问边界。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_key(self, *, tenant_id: UUID, source_execution_id: UUID, delegation_key: str) -> AgentDelegation | None:
        """按 tenant + source Execution + delegation key 查询唯一 Delegation。"""
        return (await self.db.execute(select(AgentDelegation).where(
            AgentDelegation.tenant_id == tenant_id,
            AgentDelegation.source_execution_id == source_execution_id,
            AgentDelegation.delegation_key == delegation_key,
        ))).scalar_one_or_none()

    async def list_by_source(self, *, tenant_id: UUID, source_execution_id: UUID) -> list[AgentDelegation]:
        """查询来源 Execution 的全部 Delegation，并保持租户隔离。"""
        result = await self.db.execute(select(AgentDelegation).where(
            AgentDelegation.tenant_id == tenant_id,
            AgentDelegation.source_execution_id == source_execution_id,
        ).order_by(AgentDelegation.created_at.asc(), AgentDelegation.id.asc()))
        return list(result.scalars().all())

    async def count_active(self, *, tenant_id: UUID, source_execution_id: UUID) -> int:
        """统计来源 Execution 当前活动 Delegation 数量。"""
        result = await self.db.execute(select(func.count(AgentDelegation.id)).where(
            AgentDelegation.tenant_id == tenant_id,
            AgentDelegation.source_execution_id == source_execution_id,
            AgentDelegation.status.in_(("pending", "running")),
        ))
        return int(result.scalar_one() or 0)
