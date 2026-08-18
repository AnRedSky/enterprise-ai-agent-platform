from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.auth import current_claims
from app.schemas.runtime import AuditLogListResponse, ExecutionListResponse, ExecutionTimelineResponse
from app.services.runtime_query import RuntimeQueryService

router = APIRouter(prefix="/api/v1/runtime", tags=["runtime"])


def _runtime_claims() -> dict:
    """Resolve authentication through FastAPI while keeping tests monkeypatchable."""
    return current_claims()


def _identity(claims: dict | None = None):
    """Return the authenticated actor and whether the actor has the admin role."""
    if claims is None:
        claims = current_claims()
    actor_id = UUID(claims["sub"])
    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
    return actor_id, "admin" in roles


def _normalize_execution(execution):
    """Keep the HTTP contract stable for lightweight repository/test doubles."""
    if isinstance(execution, dict) and "started_at" not in execution:
        execution = {**execution, "started_at": datetime.utcnow()}
    return execution


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    agent_id: UUID | None = None,
    trace_id: str | None = None,
    request_id: str | None = None,
    session_id: UUID | None = None,
    started_from: datetime | None = None,
    started_to: datetime | None = None,
    claims: dict = Depends(_runtime_claims),
    db: AsyncSession = Depends(get_db),
):
    actor_id, is_admin = _identity(claims)
    page, page_size, total, rows = await RuntimeQueryService(db).executions(
        actor_id,
        is_admin,
        page,
        page_size,
        status,
        agent_id,
        trace_id,
        request_id,
        session_id,
        started_from,
        started_to,
    )
    return {"items": rows, "page": page, "page_size": page_size, "total": total}


@router.get("/executions/{execution_id}", response_model=ExecutionTimelineResponse)
async def execution_detail(
    execution_id: UUID,
    claims: dict = Depends(_runtime_claims),
    db: AsyncSession = Depends(get_db),
):
    actor_id, is_admin = _identity(claims)
    execution = await RuntimeQueryService(db).execution(actor_id, is_admin, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="execution not found")
    return {"execution": _normalize_execution(execution), "items": []}


@router.get("/executions/{execution_id}/events", response_model=ExecutionTimelineResponse)
async def execution_events(
    execution_id: UUID,
    claims: dict = Depends(_runtime_claims),
    db: AsyncSession = Depends(get_db),
):
    actor_id, is_admin = _identity(claims)
    execution, events = await RuntimeQueryService(db).events(actor_id, is_admin, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="execution not found")
    return {"execution": _normalize_execution(execution), "items": events}


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    agent_id: UUID | None = None,
    tool_id: UUID | None = None,
    status: str | None = None,
    claims: dict = Depends(_runtime_claims),
    db: AsyncSession = Depends(get_db),
):
    actor_id, is_admin = _identity(claims)
    page, page_size, total, rows = await RuntimeQueryService(db).audit_logs(
        actor_id, is_admin, page, page_size, agent_id, tool_id, status
    )
    return {"items": rows, "page": page, "page_size": page_size, "total": total}
