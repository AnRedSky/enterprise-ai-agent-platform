"""Runtime Audit / Trace 关联 API。

职责：提供 Execution、Trace、AuditLog 与 Operator Action 的双向只读深链。
边界：不执行任何运维动作，不接受客户端 tenant_id；租户边界只来自认证 Claims。
关键依赖：FastAPI、RuntimeAuditTraceCorrelationService 与 Runtime correlation Schema。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims
from app.dependencies.db import get_db
from app.schemas.runtime import RuntimeCorrelationResponse
from app.services.runtime_operations.audit_trace_correlation import RuntimeAuditTraceCorrelationService

router = APIRouter(prefix="/correlations", tags=["runtime-audit-trace-correlation"])


def _claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    """解析当前认证 Claims。"""
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _tenant_id(claims: dict) -> UUID:
    """从认证上下文取得唯一租户边界。"""
    return UUID(claims["tenant_id"])


async def _query(
    method,
    identifier,
    claims: dict,
    trace_page: int,
    trace_page_size: int,
    audit_page: int,
    audit_page_size: int,
    trace_event_type: str | None,
    trace_status: str | None,
    audit_action: str | None,
    audit_status: str | None,
):
    """统一执行关联查询并在不存在时返回 404。"""
    result = await method(
        _tenant_id(claims),
        identifier,
        trace_page=trace_page,
        trace_page_size=trace_page_size,
        audit_page=audit_page,
        audit_page_size=audit_page_size,
        trace_event_type=trace_event_type,
        trace_status=trace_status,
        audit_action=audit_action,
        audit_status=audit_status,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Runtime correlation fact not found")
    return result


@router.get("/executions/{execution_id}", response_model=RuntimeCorrelationResponse)
async def execution_correlation(
    execution_id: UUID,
    trace_page: int = Query(1, ge=1),
    trace_page_size: int = Query(50, ge=1, le=100),
    audit_page: int = Query(1, ge=1),
    audit_page_size: int = Query(50, ge=1, le=100),
    trace_event_type: str | None = Query(None, min_length=1, max_length=50),
    trace_status: str | None = Query(None, min_length=1, max_length=20),
    audit_action: str | None = Query(None, min_length=1, max_length=100),
    audit_status: str | None = Query(None, min_length=1, max_length=20),
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """从 Workflow Execution 深链到 Trace、Audit 与 Operator Action。"""
    service = RuntimeAuditTraceCorrelationService(db)
    return await _query(service.by_execution, execution_id, claims, trace_page, trace_page_size, audit_page, audit_page_size,
                         trace_event_type, trace_status, audit_action, audit_status)


@router.get("/traces/{trace_id}", response_model=RuntimeCorrelationResponse)
async def trace_correlation(
    trace_id: str = Path(..., min_length=1, max_length=128),
    trace_page: int = Query(1, ge=1),
    trace_page_size: int = Query(50, ge=1, le=100),
    audit_page: int = Query(1, ge=1),
    audit_page_size: int = Query(50, ge=1, le=100),
    trace_event_type: str | None = Query(None, min_length=1, max_length=50),
    trace_status: str | None = Query(None, min_length=1, max_length=20),
    audit_action: str | None = Query(None, min_length=1, max_length=100),
    audit_status: str | None = Query(None, min_length=1, max_length=20),
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """从 Trace ID 反向定位 Execution、Audit 与 Operator Action。"""
    service = RuntimeAuditTraceCorrelationService(db)
    return await _query(service.by_trace, trace_id, claims, trace_page, trace_page_size, audit_page, audit_page_size,
                         trace_event_type, trace_status, audit_action, audit_status)


@router.get("/audits/{audit_id}", response_model=RuntimeCorrelationResponse)
async def audit_correlation(
    audit_id: UUID,
    trace_page: int = Query(1, ge=1),
    trace_page_size: int = Query(50, ge=1, le=100),
    audit_page: int = Query(1, ge=1),
    audit_page_size: int = Query(50, ge=1, le=100),
    trace_event_type: str | None = Query(None, min_length=1, max_length=50),
    trace_status: str | None = Query(None, min_length=1, max_length=20),
    audit_action: str | None = Query(None, min_length=1, max_length=100),
    audit_status: str | None = Query(None, min_length=1, max_length=20),
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """从 Audit ID 反向定位 Execution、Trace 与 Operator Action。"""
    service = RuntimeAuditTraceCorrelationService(db)
    return await _query(service.by_audit, audit_id, claims, trace_page, trace_page_size, audit_page, audit_page_size,
                         trace_event_type, trace_status, audit_action, audit_status)


@router.get("/operator-actions/{operator_action_id}", response_model=RuntimeCorrelationResponse)
async def operator_action_correlation(
    operator_action_id: UUID,
    trace_page: int = Query(1, ge=1),
    trace_page_size: int = Query(50, ge=1, le=100),
    audit_page: int = Query(1, ge=1),
    audit_page_size: int = Query(50, ge=1, le=100),
    trace_event_type: str | None = Query(None, min_length=1, max_length=50),
    trace_status: str | None = Query(None, min_length=1, max_length=20),
    audit_action: str | None = Query(None, min_length=1, max_length=100),
    audit_status: str | None = Query(None, min_length=1, max_length=20),
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """从 Operator Action 反向定位结果 Execution、Audit 与 Trace。"""
    service = RuntimeAuditTraceCorrelationService(db)
    return await _query(service.by_operator_action, operator_action_id, claims, trace_page, trace_page_size, audit_page, audit_page_size,
                         trace_event_type, trace_status, audit_action, audit_status)
