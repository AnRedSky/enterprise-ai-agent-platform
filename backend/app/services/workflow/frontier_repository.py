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


async def _has_active_node_overlap(
    db: AsyncSession, *, frontier: WorkflowFrontier,
) -> bool:
    """检查候选 Frontier 是否与同一 Execution 的活动 Frontier 重叠消费 Node。

    Args:
        db: 当前 Claim 事务使用的异步数据库会话。
        frontier: 已锁定、准备进入 claimed 状态的候选 Frontier。

    Returns:
        存在活动 Frontier 与候选 Node 集合重叠时返回 True，否则返回 False。

    设计意图：Claim 阶段必须在 Execution ownership 锁定后再次检查 Node-set fencing。
    查询本身不锁其他 Frontier，避免与 terminalization 的 Frontier → Execution 锁顺序形成死锁；
    同一 Execution 的其他 Claim 必须先取得同一 Execution 锁，因此不会在本事务的 ownership 窗口内
    并发改变 Claim 状态。若看到尚未提交的 terminalization 旧状态，本检查宁可暂时拒绝本次 Claim，
    由下一轮调度重试，也不能冒险放行重复消费。
    """
    result = await db.execute(
        select(WorkflowFrontier).where(
            WorkflowFrontier.tenant_id == frontier.tenant_id,
            WorkflowFrontier.execution_id == frontier.execution_id,
            WorkflowFrontier.id != frontier.id,
            WorkflowFrontier.status.in_(("pending", "retry_wait", "claimed", "running")),
        )
    )
    candidate_nodes = set(frontier.node_ids or [])
    return any(candidate_nodes & set(active.node_ids or []) for active in result.scalars().all())


async def claim_next_frontier(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    worker_owner: str,
    lease_expires_at: datetime,
    now: datetime,
) -> WorkflowFrontier | None:
    """Claim 一个可调度 Frontier，并在同一事务内完成 Execution 与 Node-set fencing。

    Args:
        db: 当前 Worker 持有的异步数据库会话；提交由调用方负责。
        tenant_id: 当前 Worker 要消费的租户边界。
        worker_owner: 当前 Worker ownership 标识。
        lease_expires_at: 本次 Frontier claim 使用的 Worker lease 截止时间。
        now: 当前时间，用于 available_at 与 Execution/Frontier lease 判断。

    Returns:
        已进入 claimed 状态的 Frontier；没有安全可消费 Frontier 时返回 None。

    Raises:
        ValueError: 当前候选 Frontier 与同 Execution 的活动 Frontier Node 集合重叠时不应抛出，
            而是返回 None，由上层事务 rollback 后等待下一轮调度；其他数据库错误正常向上传播。

    设计意图：同一 Execution 允许多个并行 Frontier，但不同活动 Frontier 必须拥有互斥 Node 集合。
    Claim 必须先锁定候选 Frontier，再尝试以 skip_locked 锁定 Execution，保持与 terminalization 的
    Frontier → Execution 锁顺序一致；Execution 锁成功后再检查活动 Node-set overlap。这样多个 Worker
    同时 Claim 同一 Execution 时只能串行完成 fencing，不会因为两个不同 Frontier 各自持锁而形成死锁。
    """
    now_naive = now.replace(tzinfo=None)
    execution_available = or_(
        and_(
            WorkflowExecution.status == "pending",
            or_(
                WorkflowExecution.worker_owner.is_(None),
                WorkflowExecution.worker_lease_expires_at.is_(None),
                WorkflowExecution.worker_lease_expires_at <= now_naive,
                WorkflowExecution.worker_owner == worker_owner,
            ),
        ),
        and_(
            WorkflowExecution.status == "running",
            or_(
                WorkflowExecution.worker_owner == worker_owner,
                WorkflowExecution.worker_lease_expires_at.is_(None),
                WorkflowExecution.worker_lease_expires_at <= now_naive,
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
            WorkflowFrontier.available_at <= now_naive,
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

    execution_result = await db.execute(
        select(WorkflowExecution)
        .where(
            WorkflowExecution.id == frontier.execution_id,
            WorkflowExecution.tenant_id == frontier.tenant_id,
            WorkflowExecution.status.in_(("pending", "running")),
        )
        .with_for_update(skip_locked=True)
    )
    execution = execution_result.scalar_one_or_none()
    if execution is None:
        return None

    execution_lease_expired = (
        execution.worker_lease_expires_at is None or execution.worker_lease_expires_at <= now_naive
    )
    execution_claimable = (
        execution.status == "pending"
        and (execution.worker_owner is None or execution_lease_expired or execution.worker_owner == worker_owner)
    ) or (
        execution.status == "running"
        and (execution.worker_owner == worker_owner or execution_lease_expired)
    )
    if not execution_claimable:
        return None

    if await _has_active_node_overlap(db, frontier=frontier):
        return None

    frontier.status = "claimed"
    frontier.worker_owner = worker_owner
    frontier.worker_lease_expires_at = lease_expires_at.replace(tzinfo=None)
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
