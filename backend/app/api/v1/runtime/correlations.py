"""Runtime Audit / Trace 关联 API。

职责：提供 Execution、Trace、AuditLog 与 Operator Action 的双向只读深链。
边界：不执行任何运维动作，不接受客户端 tenant_id；租户边界只来自认证 Claims。
关键依赖：FastAPI、RuntimeAuditTraceCorrelationService 与 Runtime correlation Schema。
"""

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims
from app.dependencies.db import get_db
from app.schemas.runtime import RuntimeCorrelationResponse
from app.services.runtime_operations.audit_trace_correlation import RuntimeAuditTraceCorrelationService

router = APIRouter(prefix="/correlations", tags=["runtime-audit-trace-correlation"])


def _claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict[str, str]:
    """解析当前认证 Claims。

    Args:
        credentials: FastAPI 注入的 Bearer 凭据；已在测试或内部调用中覆盖时允许为空。

    Returns:
        当前认证上下文中的 Claims 字典。
    """
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _tenant_id(claims: dict[str, str]) -> UUID:
    """从认证上下文取得唯一租户边界。

    Args:
        claims: 当前认证 Claims。

    Returns:
        当前请求所属租户 UUID。

    Raises:
        KeyError: Claims 缺少 tenant_id 时由认证上下文数据约束触发。
        ValueError: tenant_id 不是合法 UUID 时触发。
    """
    return UUID(claims["tenant_id"])


async def _query(
    method: Callable[..., dict | None],
    identifier: UUID | str,
    claims: dict[str, str],
    trace_page: int,
    trace_page_size: int,
    audit_page: int,
    audit_page_size: int,
    trace_event_type: str | None,
    trace_status: str | None,
    audit_action: str | None,
    audit_status: str | None,
) -> dict:
    """统一执行关联查询并在不存在时返回 404。

    Args:
        method: Runtime correlation Service 的 tenant-scoped 查询入口。
        identifier: 被查询的 Execution、Trace、Audit 或 Operator Action 标识。
        claims: 当前认证 Claims。
        trace_page: Trace 分页页码。
        trace_page_size: Trace 分页大小。
        audit_page: Audit 分页页码。
        audit_page_size: Audit 分页大小。
        trace_event_type: Trace 事件类型过滤条件。
        trace_status: Trace 状态过滤条件。
        audit_action: Audit 动作过滤条件。
        audit_status: Audit 状态过滤条件。

    Returns:
        Runtime correlation Service 返回的非空关联事实。

    Raises:
        HTTPException: 关联事实不存在或不属于当前租户时返回 404。
    """
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
    claims: dict[str, str] = Depends(_claims),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """从 Workflow Execution 深链到 Trace、Audit 与 Operator Action。"""
    service = RuntimeAuditTraceCorrelationService(db)
    return await _query(
        service.by_execution,
        execution_id,
        claims,
        trace_page,
        trace_page_size,
        audit_page,
        audit_page_size,
        trace_event_type,
        trace_status,
        audit_action,
        audit_status,
    )


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
    claims: dict[str, str] = Depends(_claims),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """从 Trace ID 反向定位 Execution、Audit 与 Operator Action。"""
    service = RuntimeAuditTraceCorrelationService(db)
    return await _query(
        service.by_trace,
        trace_id,
        claims,
        trace_page,
        trace_page_size,
        audit_page,
        audit_page_size,
        trace_event_type,
        trace_status,
        audit_action,
        audit_status,
    )


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
    claims: dict[str, str] = Depends(_claims),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """从 Audit ID 反向定位 Execution、Trace 与 Operator Action。"""
    service = RuntimeAuditTraceCorrelationService(db)
    return await _query(
        service.by_audit,
        audit_id,
        claims,
        trace_page,
        trace_page_size,
        audit_page,
        audit_page_size,
        trace_event_type,
        trace_status,
        audit_action,
        audit_status,
    )


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
    claims: dict[str, str] = Depends(_claims),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """从 Operator Action 反向定位结果 Execution、Audit 与 Trace。"""
    service = RuntimeAuditTraceCorrelationService(db)
    return await _query(
        service.by_operator_action,
        operator_action_id,
        claims,
        trace_page,
        trace_page_size,
        audit_page,
        audit_page_size,
        trace_event_type,
        trace_status,
        audit_action,
        audit_status,
    )
