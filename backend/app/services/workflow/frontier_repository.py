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
    """检查候选 Frontier 是否与同一 Execution 的活动 Frontier 重叠消费 Node。"""
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
        db: 当前 Worker 持有的数据库事务会话。
        tenant_id: 本次 Claim 允许消费的租户。
        worker_owner: 当前 Worker ownership 标识。
        lease_expires_at: 本次 Frontier/Execution lease 的截止时间。
        now: 当前时间，用于可调度、过期和 lease 判断。

    Returns:
        成功时返回已进入 ``claimed`` 状态并绑定当前 Worker 的 Frontier；没有安全可领取任务时返回 ``None``。

    设计意图：所有会改变同一 Execution 下 Frontier ownership 的路径统一遵循
    ``Execution → Frontier`` 锁序。候选 Frontier 首先只读选择，不提前持有 Frontier 行锁；随后先锁关联
    Execution，再锁候选 Frontier，并重新校验 Frontier 状态。这样可与 terminalization 的
    ``Execution → sibling Frontier`` 锁序一致，避免 Claim 与 completion 形成反向锁序死锁。
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

    # 这里只读选择候选，不能在这里锁 Frontier。否则会形成 Frontier → Execution 锁序，
    # 与 completion / terminalization 的 Execution → sibling Frontier 锁序相反。
    candidate_stmt = (
        select(WorkflowFrontier.id)
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
        .limit(1)
    )
    candidate_id = (await db.execute(candidate_stmt)).scalar_one_or_none()
    if candidate_id is None:
        return None

    # 先锁 Execution，统一所有同 Execution ownership 竞争路径的锁序。
    execution_id_result = await db.execute(
        select(WorkflowFrontier.execution_id, WorkflowFrontier.tenant_id)
        .where(
            WorkflowFrontier.id == candidate_id,
            WorkflowFrontier.tenant_id == tenant_id,
        )
    )
    candidate_identity = execution_id_result.one_or_none()
    if candidate_identity is None:
        return None
    candidate_execution_id, candidate_tenant_id = candidate_identity

    execution_result = await db.execute(
        select(WorkflowExecution)
        .where(
            WorkflowExecution.id == candidate_execution_id,
            WorkflowExecution.tenant_id == candidate_tenant_id,
            WorkflowExecution.status.in_(("pending", "running")),
        )
        .with_for_update(skip_locked=True)
    )
    execution = execution_result.scalar_one_or_none()
    if execution is None:
        return None

    # Execution 已锁定后再锁候选 Frontier；如果候选已被其他 Worker 消费，则本事务不再接管。
    frontier_result = await db.execute(
        select(WorkflowFrontier)
        .where(
            WorkflowFrontier.id == candidate_id,
            WorkflowFrontier.tenant_id == candidate_tenant_id,
            WorkflowFrontier.status.in_(("pending", "retry_wait")),
            WorkflowFrontier.available_at <= now_naive,
        )
        .with_for_update(skip_locked=True)
    )
    frontier = frontier_result.scalar_one_or_none()
    if frontier is None:
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
    """仅允许当前 Worker ownership、Frontier attempt 与有效 lease 同时匹配时推进 Frontier。"""
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
        raise ValueError("ownership or fencing generation mismatch")
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
) -> WorkflowFrontier:
    """释放当前 Worker 持有的 Frontier lease；其他 Worker 不得清理 ownership。"""
    if frontier.worker_owner != worker_owner:
        raise ValueError("ownership mismatch")
    frontier.worker_owner = None
    frontier.worker_lease_expires_at = None
    await db.flush()
    return frontier
