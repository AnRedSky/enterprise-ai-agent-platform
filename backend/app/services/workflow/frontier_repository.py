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
    """Claim one schedulable Frontier for a tenant without committing the transaction。

    Frontier 只有在其关联 Execution 当前允许被该 Worker 消费时才可进入 claim。
    这样可以避免 failed/completed Execution 上的旧 Frontier 阻塞其他租户或后继任务，
    同时把 Execution ownership/fencing 判断固定在 Durable Frontier claim 的事务边界内。

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
    execution_available = or_(
        and_(
            WorkflowExecution.status == "pending",
            or_(
                WorkflowExecution.worker_owner.is_(None),
                WorkflowExecution.worker_lease_expires_at.is_(None),
                WorkflowExecution.worker_lease_expires_at <= now,
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
    """只回收 Frontier 与关联 Execution 都已失去租约的可恢复任务。

    Args:
        db: 当前数据库会话。
        now: 当前时间。
        limit: 单次最多回收的 Frontier 数量。

    Returns:
        本次回收的 Frontier 列表。

    Raises:
        ValueError: limit 非正数。

    设计意图：Frontier lease 与 Execution lease 是同一个 Worker ownership 生命周期的两层事实。
    只看到 Frontier 过期而 Execution 仍持有有效 lease 时，不能立即把 Frontier 放回 retry 队列，
    否则第二个 Worker 可能在第一个 Worker 仍拥有 Execution 时抢占 Frontier，形成双重消费窗口。
    因此 running Execution 必须同时满足“无 owner 或 Execution lease 已过期”；pending Execution
    则只能在没有有效 owner 时恢复。回收动作只清除 Frontier 调度权，不递增 attempt，最终事务由调用方提交。
    """
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
    """仅允许当前 Worker ownership 与 fencing generation 匹配时推进 Frontier。

    Args:
        db: 当前数据库会话。
        frontier_id: Frontier ID。
        worker_owner: 当前 Worker ownership 标识。
        attempt: 当前 fencing generation。
        target_status: 目标状态。

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
