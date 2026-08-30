"""Global Runtime Operations API.

Protocol-only adapter for the canonical GlobalRuntimeOperationsService.
Tenant identity always comes from authenticated claims; clients cannot select a
foreign tenant.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims
from app.dependencies.db import get_db
from app.services.runtime_operations.global_operations import GlobalRuntimeOperationsService

router = APIRouter(prefix="/api/v1/runtime", tags=["runtime"])


def _claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _tenant_id(claims: dict) -> UUID:
    return UUID(claims["tenant_id"])


@router.get("/global")
async def global_runtime_operations(
    window_hours: int = Query(24, ge=1, le=168),
    workflow_id: UUID | None = Query(None),
    agent_id: UUID | None = Query(None),
    trigger_id: UUID | None = Query(None),
    execution_id: UUID | None = Query(None),
    execution_status: str | None = Query(None, min_length=1, max_length=20),
    limit: int = Query(50, ge=1, le=100),
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """Return the tenant-scoped global Execution / Workflow / Worker / Scheduler posture."""
    return await GlobalRuntimeOperationsService(db).overview(
        _tenant_id(claims),
        window_hours=window_hours,
        workflow_id=workflow_id,
        agent_id=agent_id,
        trigger_id=trigger_id,
        execution_id=execution_id,
        execution_status=execution_status,
        limit=limit,
    )
