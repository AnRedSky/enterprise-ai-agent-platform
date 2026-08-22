from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.auth import bearer, current_claims
from app.models.execution import Execution
from app.schemas.runtime import AuditLogListResponse, ExecutionListResponse, ExecutionTimelineResponse, WorkflowTraceResponse
from app.services.runtime_query import RuntimeQueryService
from app.services.workflow_execution import WorkflowExecutionService

router = APIRouter(prefix="/api/v1/runtime", tags=["runtime"])


def _runtime_claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _identity(claims: dict | None = None):
    if claims is None:
        claims = current_claims()
    actor_id = UUID(claims["sub"])
    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
    return actor_id, "admin" in roles


def _tenant_id(claims: dict) -> UUID:
    return UUID(claims["tenant_id"])


def _normalize_execution(execution):
    if isinstance(execution, dict) and "started_at" not in execution:
        execution = {**execution, "started_at": datetime.now(UTC)}
    return execution


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                          status: str | None = None, agent_id: UUID | None = None,
                          trace_id: str | None = None, request_id: str | None = None,
                          session_id: UUID | None = None, started_from: datetime | None = None,
                          started_to: datetime | None = None, claims: dict = Depends(_runtime_claims),
                          db: AsyncSession = Depends(get_db)):
    actor_id, is_admin = _identity(claims)
    page, page_size, total, rows = await RuntimeQueryService(db).executions(
        actor_id, is_admin, page, page_size, status, agent_id, trace_id, request_id,
        session_id, started_from, started_to,
    )
    return {"items": rows, "page": page, "page_size": page_size, "total": total}


@router.get("/executions/{execution_id}", response_model=ExecutionTimelineResponse)
async def execution_detail(execution_id: UUID, claims: dict = Depends(_runtime_claims), db: AsyncSession = Depends(get_db)):
    actor_id, is_admin = _identity(claims)
    execution, events = await RuntimeQueryService(db).events(actor_id, is_admin, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="execution not found")
    return {"execution": _normalize_execution(execution), "items": events}


@router.get("/executions/{execution_id}/events", response_model=ExecutionTimelineResponse)
async def execution_events(execution_id: UUID, claims: dict = Depends(_runtime_claims), db: AsyncSession = Depends(get_db)):
    return await execution_detail(execution_id, claims, db)


@router.get("/executions/{execution_id}/trace", response_model=WorkflowTraceResponse)
async def workflow_execution_trace(execution_id: UUID, claims: dict = Depends(_runtime_claims), db: AsyncSession = Depends(get_db)):
    actor_id, is_admin = _identity(claims)
    execution = await WorkflowExecutionService(db).get(execution_id, _tenant_id(claims), actor_id, is_admin)
    rows = await RuntimeQueryService(db).workflow_trace(actor_id, is_admin, execution_id, execution.tenant_id)
    return {"execution_id": execution.id, "items": rows}


@router.get("/retrieval-evaluations/{evaluation_run_id}", response_model=ExecutionTimelineResponse)
async def retrieval_evaluation_trace(evaluation_run_id: UUID, claims: dict = Depends(_runtime_claims), db: AsyncSession = Depends(get_db)):
    _, is_admin = _identity(claims)
    if not is_admin:
        raise HTTPException(status_code=403, detail="retrieval evaluation trace requires admin role")
    execution = (await db.execute(select(Execution).where(Execution.trace_id == str(evaluation_run_id)))).scalar_one_or_none()
    if execution is None:
        raise HTTPException(status_code=404, detail="retrieval evaluation not found")
    _, events = await RuntimeQueryService(db).events(UUID(claims["sub"]), True, execution.id)
    return {"execution": _normalize_execution(execution), "items": events}


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                          agent_id: UUID | None = None, tool_id: UUID | None = None,
                          workflow_id: UUID | None = None, workflow_execution_id: UUID | None = None,
                          status: str | None = None, claims: dict = Depends(_runtime_claims),
                          db: AsyncSession = Depends(get_db)):
    actor_id, is_admin = _identity(claims)
    page, page_size, total, rows = await RuntimeQueryService(db).audit_logs(
        actor_id, is_admin, page, page_size, agent_id, tool_id, status, workflow_id, workflow_execution_id,
    )
    return {"items": rows, "page": page, "page_size": page_size, "total": total}
