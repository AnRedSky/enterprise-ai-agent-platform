"""Enterprise Runtime Global Operations posture.

This module provides a read-only, tenant-scoped operational view across the
existing durable Workflow / Execution / Frontier / Trigger facts.  It does not
introduce a second lifecycle, scheduler, or worker state machine.

Important boundary:
- WorkflowExecutionService remains the authority for execution lifecycle.
- WorkflowTriggerService remains the authority for trigger lifecycle.
- WorkflowFrontier is the durable worker-claim fact source.
- There is currently no durable scheduler/worker heartbeat fact, so process
  liveness is reported as ``unknown`` instead of being inferred from activity.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.models.workflow_trigger import WorkflowTrigger


class GlobalRuntimeOperationsService:
    """Build a read-only global runtime posture from canonical durable facts."""

    MAX_WINDOW_HOURS = 168
    MAX_ITEMS = 100
    _EXECUTION_STATUSES = ("pending", "running", "completed", "failed", "cancelled")
    _FRONTIER_STATUSES = ("pending", "running", "completed", "failed", "cancelled")

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @classmethod
    def _window(cls, window_hours: int) -> tuple[int, datetime]:
        bounded = min(max(window_hours, 1), cls.MAX_WINDOW_HOURS)
        return bounded, datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=bounded)

    @staticmethod
    def _counts(rows: list[tuple[str, int]]) -> dict[str, int]:
        return {status: int(count) for status, count in rows}

    async def overview(
        self,
        tenant_id: UUID,
        *,
        window_hours: int = 24,
        workflow_id: UUID | None = None,
        trigger_id: UUID | None = None,
        execution_id: UUID | None = None,
        execution_status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return the tenant's global runtime posture.

        Filters are applied server-side and always retain the tenant boundary.
        ``workflow_id``, ``trigger_id`` and ``execution_id`` are correlation
        filters; ``execution_status`` is an execution-state filter.

        Worker posture is derived from durable frontier claims. Scheduler
        posture intentionally reports process liveness as ``unknown`` because
        the current platform has no durable scheduler heartbeat contract.
        """
        window_hours, since = self._window(window_hours)
        limit = min(max(limit, 1), self.MAX_ITEMS)

        execution_filters = [
            WorkflowExecution.tenant_id == tenant_id,
            WorkflowExecution.created_at >= since,
        ]
        if workflow_id is not None:
            execution_filters.append(WorkflowExecution.workflow_id == workflow_id)
        if execution_id is not None:
            execution_filters.append(WorkflowExecution.id == execution_id)
        if execution_status is not None:
            if execution_status not in self._EXECUTION_STATUSES:
                raise ValueError("unsupported execution_status")
            execution_filters.append(WorkflowExecution.status == execution_status)

        execution_rows = (await self.db.execute(
            select(WorkflowExecution.status, func.count())
            .where(*execution_filters)
            .group_by(WorkflowExecution.status)
        )).all()
        execution_counts = self._counts(execution_rows)

        workflow_filters = [Workflow.tenant_id == tenant_id]
        if workflow_id is not None:
            workflow_filters.append(Workflow.id == workflow_id)
        workflow_rows = (await self.db.execute(
            select(Workflow.status, func.count())
            .where(*workflow_filters)
            .group_by(Workflow.status)
        )).all()
        workflow_counts = self._counts(workflow_rows)

        trigger_filters = [WorkflowTrigger.tenant_id == tenant_id]
        if workflow_id is not None:
            trigger_filters.append(WorkflowTrigger.workflow_id == workflow_id)
        if trigger_id is not None:
            trigger_filters.append(WorkflowTrigger.id == trigger_id)
        trigger_rows = (await self.db.execute(
            select(WorkflowTrigger.status, func.count())
            .where(*trigger_filters)
            .group_by(WorkflowTrigger.status)
        )).all()
        trigger_counts = self._counts(trigger_rows)

        frontier_filters = [
            WorkflowFrontier.tenant_id == tenant_id,
            WorkflowFrontier.created_at >= since,
        ]
        if workflow_id is not None:
            frontier_filters.append(
                WorkflowFrontier.execution_id.in_(
                    select(WorkflowExecution.id).where(
                        WorkflowExecution.tenant_id == tenant_id,
                        WorkflowExecution.workflow_id == workflow_id,
                    )
                )
            )
        if execution_id is not None:
            frontier_filters.append(WorkflowFrontier.execution_id == execution_id)

        frontier_rows = (await self.db.execute(
            select(WorkflowFrontier.status, func.count())
            .where(*frontier_filters)
            .group_by(WorkflowFrontier.status)
        )).all()
        frontier_counts = self._counts(frontier_rows)

        now = datetime.now(UTC).replace(tzinfo=None)
        leased_count = await self.db.scalar(
            select(func.count()).select_from(WorkflowFrontier).where(
                *frontier_filters,
                WorkflowFrontier.worker_owner.is_not(None),
                WorkflowFrontier.worker_lease_expires_at.is_not(None),
                WorkflowFrontier.status == "running",
            )
        ) or 0
        expired_lease_count = await self.db.scalar(
            select(func.count()).select_from(WorkflowFrontier).where(
                *frontier_filters,
                WorkflowFrontier.worker_lease_expires_at.is_not(None),
                WorkflowFrontier.worker_lease_expires_at < now,
                WorkflowFrontier.status == "running",
            )
        ) or 0
        worker_owners = await self.db.scalar(
            select(func.count(func.distinct(WorkflowFrontier.worker_owner))).select_from(WorkflowFrontier).where(
                *frontier_filters,
                WorkflowFrontier.worker_owner.is_not(None),
                WorkflowFrontier.status == "running",
            )
        ) or 0

        scheduled_trigger_filters = [
            WorkflowTrigger.tenant_id == tenant_id,
            WorkflowTrigger.trigger_type == "schedule",
            WorkflowTrigger.status == "enabled",
        ]
        if workflow_id is not None:
            scheduled_trigger_filters.append(WorkflowTrigger.workflow_id == workflow_id)
        scheduled_enabled = await self.db.scalar(
            select(func.count()).select_from(WorkflowTrigger).where(*scheduled_trigger_filters)
        ) or 0

        recent_stmt = (
            select(WorkflowExecution, Workflow.name)
            .join(Workflow, Workflow.id == WorkflowExecution.workflow_id)
            .where(*execution_filters)
            .order_by(WorkflowExecution.created_at.desc(), WorkflowExecution.id.desc())
            .limit(limit)
        )
        recent_rows = (await self.db.execute(recent_stmt)).all()
        recent_executions = [
            {
                "id": execution.id,
                "workflow_id": execution.workflow_id,
                "workflow_name": workflow_name,
                "status": execution.status,
                "current_node_id": execution.current_node_id,
                "worker_owner": execution.worker_owner,
                "worker_attempt": execution.worker_attempt,
                "worker_lease_expires_at": execution.worker_lease_expires_at,
                "error_code": execution.error_code,
                "started_at": execution.started_at,
                "ended_at": execution.ended_at,
                "created_at": execution.created_at,
            }
            for execution, workflow_name in recent_rows
        ]

        active_execution_count = execution_counts.get("pending", 0) + execution_counts.get("running", 0)
        recovery_count = execution_counts.get("failed", 0)
        scheduler_backlog = frontier_counts.get("pending", 0)

        return {
            "window_hours": window_hours,
            "since": since,
            "generated_at": datetime.now(UTC),
            "filters": {
                "workflow_id": workflow_id,
                "trigger_id": trigger_id,
                "execution_id": execution_id,
                "execution_status": execution_status,
            },
            "executions": {
                "total": sum(execution_counts.values()),
                "status_counts": execution_counts,
                "active_count": active_execution_count,
                "recovery_count": recovery_count,
                "items": recent_executions,
            },
            "workflows": {
                "total": sum(workflow_counts.values()),
                "status_counts": workflow_counts,
            },
            "triggers": {
                "total": sum(trigger_counts.values()),
                "status_counts": trigger_counts,
                "scheduled_enabled": int(scheduled_enabled),
            },
            "worker": {
                "liveness": "unknown",
                "liveness_reason_code": "NO_DURABLE_HEARTBEAT_FACT",
                "running_frontiers": frontier_counts.get("running", 0),
                "pending_frontiers": frontier_counts.get("pending", 0),
                "leased_frontiers": int(leased_count),
                "expired_leases": int(expired_lease_count),
                "active_worker_owners": int(worker_owners),
            },
            "scheduler": {
                "liveness": "unknown",
                "liveness_reason_code": "NO_DURABLE_HEARTBEAT_FACT",
                "enabled_scheduled_triggers": int(scheduled_enabled),
                "durable_frontier_backlog": int(scheduler_backlog),
            },
        }
