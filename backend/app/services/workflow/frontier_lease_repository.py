"""Durable Frontier lease repository boundary.

职责：提供 Frontier Worker lease heartbeat 的原子续租操作。
边界：不负责 Claim、Runtime 执行或 Scheduler；所有状态与 ownership 变更仍通过 workflow_frontiers 数据库边界完成。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier


async def renew_owned_frontier_lease(
    db: AsyncSession,
    *,
    frontier_id: UUID,
    worker_owner: str,
    attempt: int,
    lease_expires_at: datetime,
    now: datetime,
) -> bool:
    """原子刷新 Frontier 与其 Execution lease，不提交事务。

    Frontier 与 Execution 是同一个 Worker runtime 的两层 ownership contract；只刷新 Frontier
    会产生“Frontier lease 仍有效、Execution lease 已过期”的跨层 stale-worker 窗口。因此 heartbeat
    必须在同一短事务内同时证明并刷新两层 lease。任一层 ownership/fencing/status/lease 无效时，
    不保留任何续租结果，由调用方 rollback。
    """
    frontier_result = await db.execute(
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
    if frontier_result.rowcount != 1:
        await db.rollback()
        return False

    execution_id_result = await db.execute(
        select(WorkflowFrontier.execution_id).where(WorkflowFrontier.id == frontier_id)
    )
    execution_id = execution_id_result.scalar_one_or_none()
    if execution_id is None:
        await db.rollback()
        return False

    execution_result = await db.execute(
        update(WorkflowExecution)
        .where(
            WorkflowExecution.id == execution_id,
            WorkflowExecution.worker_owner == worker_owner,
            WorkflowExecution.status.in_(("pending", "running")),
            WorkflowExecution.worker_lease_expires_at > now,
        )
        .values(worker_lease_expires_at=lease_expires_at)
        .execution_options(synchronize_session=False)
    )
    if execution_result.rowcount != 1:
        await db.rollback()
        return False

    await db.flush()
    return True
