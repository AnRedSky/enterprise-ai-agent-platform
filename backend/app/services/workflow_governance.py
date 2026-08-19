from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent


class WorkflowGovernanceService:
    """Persist immutable governance/audit facts and execution trace events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def audit(self, execution: WorkflowExecution, actor_id: UUID | None, action: str, status: str,
                    *, error_code: str | None = None, metadata: dict[str, Any] | None = None) -> AuditLog:
        event = AuditLog(
            actor_id=actor_id,
            tenant_id=execution.tenant_id,
            workflow_id=execution.workflow_id,
            workflow_version_id=execution.workflow_version_id,
            workflow_execution_id=execution.id,
            action=action,
            resource_type="workflow_execution",
            resource_id=str(execution.id),
            trace_id=str(execution.id),
            status=status,
            error_code=error_code,
            metadata_json=metadata,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def trace(self, execution: WorkflowExecution, actor_id: UUID | None, event_type: str, status: str,
                    *, node_id: str | None = None, data: dict[str, Any] | None = None,
                    error_code: str | None = None, error_message: str | None = None) -> WorkflowTraceEvent:
        event = WorkflowTraceEvent(
            tenant_id=execution.tenant_id,
            execution_id=execution.id,
            workflow_id=execution.workflow_id,
            workflow_version_id=execution.workflow_version_id,
            node_id=node_id,
            event_type=event_type,
            status=status,
            trace_id=str(execution.id),
            actor_id=actor_id,
            data=data,
            error_code=error_code,
            error_message=error_message,
        )
        self.db.add(event)
        await self.db.flush()
        return event
