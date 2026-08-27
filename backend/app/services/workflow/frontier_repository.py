"""Durable Workflow Frontier repository primitives.

职责：封装 Frontier 的幂等创建、Claim、租约恢复和 Worker fencing 数据库操作。
边界：不负责 DAG Planner、Scheduler 时间计算或 Workflow Runtime 执行；Scheduler/Worker 调用方拥有外层事务。
关键依赖：SQLAlchemy AsyncSession、PostgreSQL 唯一约束，以及 WorkflowFrontierIdentity 领域契约。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowFrontier
from app.services.workflow.frontier import WorkflowFrontierIdentity


async def enqueue_frontier(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    identity: WorkflowFrontierIdentity,
    node_ids: tuple[str, ...],
    now: datetime,
) -> WorkflowFrontier:
    """幂等创建一个待调度 Frontier，并保持事务由调用方拥有。

    Args:
        db: 当前数据库会话。
        tenant_id: 当前租户 ID，必须与 Execution 所属租户一致。
        identity: Planner 产生的确定性 Frontier 身份。
        node_ids: 当前 Frontier 的有序节点集合。
        now: Frontier 可调度时间。

    Returns:
        已创建或已经存在的 Durable Frontier。

    Raises:
        RuntimeError: 数据库唯一约束发生并发竞争后仍无法读取 Frontier。

    事务边界：这里只执行 INSERT/SELECT 与 flush，不执行 commit；Scheduler/Worker 必须在自己的原子事务中提交。
    """
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
    """Claim one schedulable Frontier for a tenant without committing the transaction.

    Args:
        db: 当前数据库会话。
        tenant_id: 当前租户 ID。
        worker_owner: 当前 Worker ownership 标识。
        lease_expires_at: 本次 Worker lease 到期时间。
        now: 当前时间。

    Returns:
        成功认领的 Frontier；没有可调度任务时返回 None。

    事务边界：只锁定、修改并 flush Frontier，不执行 commit；调用方负责最终事务提交。
    """
    stmt = (
        select(WorkflowFrontier)
        .where(
            WorkflowFrontier.tenant_id == tenant_id,
            WorkflowFrontier.status.in_(("pending", "retry_wait")),
            WorkflowFrontier.available_at <= now,
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
    """Move expired claimed/running Frontiers back to retry_wait without committing.

    Args:
        db: 当前数据库会话。
        now: 当前时间。
        limit: 单次最多回收的 Frontier 数量。

    Returns:
        本次回收的 Frontier 列表。

    Raises:
        ValueError: limit 非正数。

    设计意图：过期租约只回收调度权，不直接递增 attempt；下一次成功 Claim 才产生新的 fencing generation。
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    stmt = (
        select(WorkflowFrontier)
        .where(
            WorkflowFrontier.status.in_(("claimed", "running")),
            WorkflowFrontier.worker_lease_expires_at.is_not(None),
            WorkflowFrontier.worker_lease_expires_at <= now,
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
    """仅允许当前 Worker ownership 与 fencing generation 匹配时推进 Frontier。

    Args:
        db: 当前数据库会话。
        frontier_id: Frontier ID。
        worker_owner: 当前 Worker ownership 标识。
        attempt: 当前 fencing generation。
        target_status: 目标状态。
        now: 当前时间。

    Returns:
        完成状态变更后的 Frontier。

    Raises:
        ValueError: ownership、attempt 或当前状态不满足要求。

    事务边界：只执行带行锁的状态变更与 flush，不执行 commit。
    """
    result = await db.execute(
        select(WorkflowFrontier)
        .where(
            WorkflowFrontier.id == frontier_id,
            WorkflowFrontier.worker_owner == worker_owner,
            WorkflowFrontier.attempt == attempt,
            WorkflowFrontier.status.in_(("claimed", "running")),
        )
        .with_for_update()
    )
    frontier = result.scalar_one_or_none()
    if frontier is None:
        raise ValueError("Frontier worker ownership or fencing generation mismatch")
    frontier.status = target_status
    frontier.completed_at = now if target_status in ("completed", "failed") else None
    if target_status in ("completed", "failed", "retry_wait"):
        frontier.worker_owner = None
        frontier.worker_lease_expires_at = None
    await db.flush()
    return frontier


async def release_frontier_lease(
    db: AsyncSession,
    *,
    frontier: WorkflowFrontier,
    worker_owner: str,
) -> None:
    """释放仍由指定 Worker 持有的 Frontier lease，不执行 commit。

    Args:
        db: 当前数据库会话。
        frontier: 当前 Frontier ORM 实体。
        worker_owner: 请求释放 lease 的 Worker ownership。

    Returns:
        无返回值。

    Raises:
        ValueError: Frontier 已不属于当前 Worker。
    """
    if frontier.worker_owner != worker_owner:
        raise ValueError("Frontier worker ownership mismatch")
    frontier.worker_owner = None
    frontier.worker_lease_expires_at = None
    await db.flush()
