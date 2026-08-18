from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.auth import current_claims
from app.schemas.runtime import AuditLogListResponse, ExecutionEventItem, ExecutionListResponse, ExecutionTimelineResponse
from app.services.runtime_query import RuntimeQueryService

router = APIRouter(prefix="/api/v1/runtime", tags=["runtime"])


def _identity():
    claims = current_claims()
    actor_id = UUID(claims["sub"])
    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
    return actor_id, "admin" in roles


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), status: str | None = None,
    agent_id: UUID | None = None, trace_id: str | None = None, request_id: str | None = None,
    session_id: UUID | None = None, started_from: datetime | None = None, started_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
):
    actor_id, is_admin = _identity()
    service = RuntimeQueryService(db)
    page, page_size, total, rows = await service.executions(actor_id, is_admin, page, page_size, status, agent_id, trace_id, request_id, session_id, started_from, started_to)
    return {"items": rows, "page": page, "page_size": page_size, "total": total}


@router.get("/executions/{execution_id}/events", response_model=ExecutionTimelineResponse)
async def execution_events(execution_id: UUID, db: AsyncSession = Depends(get_db)):
    actor_id, is_admin = _identity()
    execution, events = await RuntimeQueryService(db).events(actor_id, is_admin, execution_id)
    if execution is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="execution not found")
    return {"execution": execution, "items": events}


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), agent_id: UUID | None = None,
    tool_id: UUID | None = None, status: str | None = None, db: AsyncSession = Depends(get_db),
):
    actor_id, is_admin = _identity()
    page, page_size, total, rows = await RuntimeQueryService(db).audit_logs(actor_id, is_admin, page, page_size, agent_id, tool_id, status)
    return {"items": rows, "page": page, "page_size": page_size, "total": total}
