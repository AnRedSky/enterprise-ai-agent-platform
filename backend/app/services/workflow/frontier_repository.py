"""Durable Workflow Frontier repository primitives。

职责：封装 Frontier 的幂等创建、Claim、租约恢复和 Worker fencing 数据库操作。
边界：不负责 DAG Planner、Scheduler 时间计算或 Workflow Runtime 执行；Scheduler/Worker 调用方拥有外层事务。
关键依赖：SQLAlchemy AsyncSession、PostgreSQL 唯一约束，以及 WorkflowFrontierIdentity 领域契约。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.services.workflow.frontier import WorkflowFrontierIdentity


def _execution_recoverable_filter(now: datetime):
    """生成 Execution lease 可回收条件，避免 Frontier 单独过期造成双 Worker 消费。

    Args:
        now: 当前时间。

    Returns:
        SQLAlchemy 条件表达式：Execution 没有 owner、没有 lease，或 lease 已过期。

    设计意图：Frontier 与 Execution 是同一个 Worker ownership 生命周期的两层 durable fact。
    恢复 Frontier 前必须同时确认 Execution 已失去有效租约，否则旧 Worker 仍可能持有 Execution
    并继续执行，新的 Worker 却已经获得同一个 Frontier，形成重复消费窗口。
    """
    return or_(
        WorkflowExecution.worker_owner.is_(None),
        WorkflowExecution.worker_lease_expires_at.is_(None),
        WorkflowExecution.worker_lease_expires_at <= now,
    )


async def enqueue_frontier(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    identity: WorkflowFrontierIdentity,
    node_ids: tuple[str, ...],
    now: datetime,
) -> WorkflowFrontier:
    """幂等创建一个待调度 Frontier，并保持事务由调用方拥有。"""
    frontier_key = identity.key()
    statement = (
        pg_insert(WorkflowFrontier)
        .values(
            tenant_id=tenant_id,
            execution_id=identity.execution_id,
            workflow_version_id=identity.workflow_version_id,
            decision_fingerprint=identity.decision_fingerprint,
            frontier_key=frontier_key,
            node_ids=list(node_ids),
            status="pending",
            attempt=0,
            available_at=now,
        )
        .on_conflict_do_nothing(constraint="uq_workflow_frontier_tenant_key")
        .returning(WorkflowFrontier.id)
    )
    frontier_id = (await db.execute(statement)).scalar_one_or_none()
    if frontier_id is None:
        existing = (
            await db.execute(
                select(WorkflowFrontier).where(
                    WorkflowFrontier.tenant_id == tenant_id,
                    WorkflowFrontier.frontier_key == frontier_key,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            raise RuntimeError("Durable Frontier 并发创建未收敛")
        return existing
    frontier = (
        await db.execute(select(WorkflowFrontier).where(WorkflowFrontier.id == frontier_id))
    ).scalar_one()
    await db.flush()
    return frontier


async def claim_next_frontier(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    worker_owner: str,
    lease_expires_at: datetime,
    now: datetime,
) -> WorkflowFrontier | None:
    """Claim one schedulable Frontier for a tenant without committing the transaction。

    Frontier 只有在其关联 Execution 当前允许被该 Worker 消费时才可进入 claim。
    这样可以避免 failed/completed Execution 上的旧 Frontier 阻塞其他租户或后继任务，
    同时把 Execution ownership/fencing 判断固定在 Durable Frontier claim 的事务边界内。

    Recovery 后一个 Execution 可能同时存在多个 retry_wait Frontier；当 pending Execution 已经由
    当前 Worker 重新取得 ownership 时，后续 Frontier 可以复用同一 Worker epoch，不应被 pending
    状态本身错误阻塞。
    """
    execution_available = or_(
        and_(
            WorkflowExecution.status == "pending",
            or_(
                WorkflowExecution.worker_owner.is_(None),
                WorkflowExecution.worker_lease_expires_at.is_(None),
                WorkflowExecution.worker_lease_expires_at <= now,
                WorkflowExecution.worker_owner == worker_owner,
            ),
        ),
        and_(
            WorkflowExecution.status == "running",
            or_(
                WorkflowExecution.worker_owner == worker_owner,
                WorkflowExecution.worker_lease_expires_at.is_(None),
                WorkflowExecution.worker_lease_expires_at <= now,
            ),
        ),
    )
    stmt = (
        select(WorkflowFrontier)
        .join(
            WorkflowExecution,
            and_(
                WorkflowExecution.id == WorkflowFrontier.execution_id,
                WorkflowExecution.tenant_id == WorkflowFrontier.tenant_id,
            ),
        )
        .where(
            WorkflowFrontier.tenant_id == tenant_id,
            WorkflowFrontier.status.in_(("pending", "retry_wait")),
            WorkflowFrontier.available_at <= now,
            execution_available,
        )
        .order_by(WorkflowFrontier.available_at, WorkflowFrontier.created_at, WorkflowFrontier.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    result = await db.execute(stmt)
    frontier = result.scalar_one_or_none()
    if frontier is None:
        return None

    frontier.status = "claimed"
    frontier.worker_owner = worker_owner
    frontier.worker_lease_expires_at = lease_expires_at
    frontier.attempt += 1
    await db.flush()
    return frontier


async def recover_expired_frontiers(
    db: AsyncSession,
    *,
    now: datetime,
    limit: int = 100,
) -> list[WorkflowFrontier]:
    """只回收 Frontier 与关联 Execution 都已失去租约的可恢复任务。"""
    if limit <= 0:
        raise ValueError("limit must be positive")
    stmt = (
        select(WorkflowFrontier)
        .join(
            WorkflowExecution,
            and_(
                WorkflowExecution.id == WorkflowFrontier.execution_id,
                WorkflowExecution.tenant_id == WorkflowFrontier.tenant_id,
            ),
        )
        .where(
            WorkflowFrontier.status.in_(("claimed", "running")),
            WorkflowFrontier.worker_lease_expires_at.is_not(None),
            WorkflowFrontier.worker_lease_expires_at <= now,
            WorkflowExecution.status.in_(("pending", "running")),
            _execution_recoverable_filter(now),
        )
        .order_by(WorkflowFrontier.worker_lease_expires_at, WorkflowFrontier.created_at, WorkflowFrontier.id)
        .with_for_update(skip_locked=True)
        .limit(limit)
    )
    frontiers = list((await db.execute(stmt)).scalars().all())
    for frontier in frontiers:
        frontier.status = "retry_wait"
        frontier.worker_owner = None
        frontier.worker_lease_expires_at = None
        frontier.available_at = now
        frontier.error_code = "FRONTIER_LEASE_EXPIRED"
        frontier.error_message = "Worker lease expired; Frontier returned to retry queue"
    if frontiers:
        await db.flush()
    return frontiers


async def transition_owned_frontier(
    db: AsyncSession,
    *,
    frontier_id: UUID,
    worker_owner: str,
    attempt: int,
    target_status: str,
    now: datetime,
) -> WorkflowFrontier:
    """仅允许当前 Worker ownership、Frontier attempt 与有效 lease 同时匹配时推进 Frontier。

    Args:
        db: 当前调用方持有的异步数据库会话。
        frontier_id: 要推进的 Durable Frontier 标识。
        worker_owner: 当前 Worker ownership 标识。
        attempt: 当前 Frontier consumption attempt，用于 fencing 旧 Worker。
        target_status: 目标 Frontier 状态。
        now: 当前时间；必须用于判断 Worker lease 是否仍然有效。

    Returns:
        已完成状态变更并 flush 的 WorkflowFrontier。

    Raises:
        ValueError: Frontier 不再属于当前 Worker、attempt 已变化或 lease 已失效。

    设计意图：仅校验 owner + attempt 不能阻止“lease 已过期但旧 Worker 尚未被 Recovery 清理”的并发窗口。
    因此最终状态推进必须把有效 lease 一并纳入数据库锁定条件，让 stale Worker 的 completion/failure
    在 Recovery 抢先或并发竞争时都无法写入 Durable terminal state。
    """
    result = await db.execute(
        select(WorkflowFrontier)
        .where(
            WorkflowFrontier.id == frontier_id,
            WorkflowFrontier.worker_owner == worker_owner,
            WorkflowFrontier.attempt == attempt,
            WorkflowFrontier.worker_lease_expires_at.is_not(None),
            WorkflowFrontier.worker_lease_expires_at > now,
            WorkflowFrontier.status.in_(("claimed", "running")),
        )
        .with_for_update()
    )
    frontier = result.scalar_one_or_none()
    if frontier is None:
        raise ValueError("Frontier worker ownership, fencing generation or lease validity mismatch")
    frontier.status = target_status
    frontier.completed_at = now if target_status in ("completed", "failed") else None
    if target_status in ("completed", "failed", "retry_wait"):
        frontier.worker_owner = None
        frontier.worker_lease_expires_at = None
    await db.flush()
    return frontier
