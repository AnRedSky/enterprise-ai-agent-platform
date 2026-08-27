"""Durable Frontier lease repository boundary.

职责：提供 Frontier Worker lease heartbeat 的原子续租操作。
边界：不负责 Claim、Runtime 执行或 Scheduler；所有状态与 ownership 变更仍通过 workflow_frontiers 数据库边界完成。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowFrontier


async def renew_owned_frontier_lease(
    db: AsyncSession,
    *,
    frontier_id: UUID,
    worker_owner: str,
    attempt: int,
    lease_expires_at: datetime,
    now: datetime,
) -> bool:
    """仅当前 Worker + fencing generation 仍有效时刷新 Frontier lease，不提交事务。"""
    result = await db.execute(
        update(WorkflowFrontier)
        .where(
            WorkflowFrontier.id == frontier_id,
            WorkflowFrontier.worker_owner == worker_owner,
            WorkflowFrontier.attempt == attempt,
            WorkflowFrontier.status.in_(("claimed", "running")),
            WorkflowFrontier.worker_lease_expires_at > now,
        )
        .values(worker_lease_expires_at=lease_expires_at)
        .execution_options(synchronize_session=False)
    )
    await db.flush()
    return result.rowcount == 1
