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
    Frontiers while preserving tenant isolation. The caller must commit the
    successful claim and may roll it back as part of its larger transaction.
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
