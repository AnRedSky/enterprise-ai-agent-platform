"""Durable Frontier lease repository boundary。

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

    Args:
        db: 当前异步数据库会话。
        frontier_id: 当前 Frontier 标识。
        worker_owner: 当前 Worker ownership 标识。
        attempt: 当前 Frontier fencing generation。
        lease_expires_at: 新的 lease 截止时间。
        now: 当前时间，用于验证 lease 尚未失效。

    Returns:
        bool: 两层 lease 均成功刷新且仍由当前 Worker 持有时返回 True，否则返回 False。

    Raises:
        Exception: 数据库操作失败时由调用方处理并决定是否重试。

    事务边界：Frontier 与 Execution 是同一个 Worker runtime 的两层 ownership contract；只刷新
    Frontier 会产生“Frontier lease 仍有效、Execution lease 已过期”的跨层 stale-worker 窗口。
    因此 heartbeat 必须在同一短事务内同时证明并刷新两层 lease。所有涉及同一 Execution 的
    ownership 事务统一采用 ``Execution → Frontier`` 锁序：先更新带 ownership fencing 的
    WorkflowExecution，再更新 WorkflowFrontier。这样可以与 Claim 的 ``Execution → Frontier``
    锁序一致，避免 heartbeat 与 Claim/terminalization 形成 PostgreSQL 反向锁等待。
    """
    # 这里只读取得关联 Execution ID，不提前锁 Frontier。这样 heartbeat 不会形成
    # Frontier → Execution 的反向锁序。
    execution_id_result = await db.execute(
        select(WorkflowFrontier.execution_id).where(
            WorkflowFrontier.id == frontier_id,
            WorkflowFrontier.tenant_id.is_not(None),
        )
    )
    execution_id = execution_id_result.scalar_one_or_none()
    if execution_id is None:
        await db.rollback()
        return False

    # 先更新 Execution，与 Frontier Claim/terminalization 保持统一锁序。
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

    # Execution ownership 已证明后，再更新同一 attempt 的 Frontier lease。
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

    await db.flush()
    return True
