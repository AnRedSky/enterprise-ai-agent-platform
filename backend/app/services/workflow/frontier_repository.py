"""Durable Workflow Frontier repository primitives.

Repository methods intentionally do not commit. Scheduler/Worker callers own the
outer transaction, matching the workflow transaction ownership contract.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowFrontier


async def claim_next_frontier(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    worker_owner: str,
    lease_expires_at: datetime,
    now: datetime,
) -> WorkflowFrontier | None:
    """Claim one schedulable Frontier for a tenant without committing the transaction.

    ``FOR UPDATE SKIP LOCKED`` allows concurrent Workers to claim different
    Frontiers while preserving tenant isolation. ``attempt`` is the fencing
    generation: every successful reclaim receives a new generation.
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
    """Move expired claimed/running Frontiers back to ``retry_wait``.

    The rows are locked before mutation and ``SKIP LOCKED`` prevents a recovery
    sweep from racing with an active Worker transaction. Recovery clears the
    previous owner; a subsequent claim increments the fencing generation.
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
    """Transition a Frontier only when owner and fencing generation still match.

    A stale Worker therefore cannot complete, fail, or otherwise mutate a
    Frontier after another Worker has reclaimed its expired lease.
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
    """Release a lease only when the caller still owns the Frontier."""
    if frontier.worker_owner != worker_owner:
        raise ValueError("Frontier worker ownership mismatch")
    frontier.worker_owner = None
    frontier.worker_lease_expires_at = None
    await db.flush()
