"""Runtime Operator Action 审计查询 API。

职责：暴露基于 AuditLog 唯一事实源的 Operator Action 审计只读查询。
边界：不执行 Operator Action、不修改审计事实、不接受客户端 tenant_id。
关键依赖：OperatorAuditQueryService、FastAPI 认证上下文与数据库 Session。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims
from app.dependencies.db import get_db
from app.services.runtime_operations import OperatorAuditQueryService


router = APIRouter(prefix="/api/v1/runtime/operations/operator-audits", tags=["runtime-operator-audit"])


class OperatorAuditItem(BaseModel):
    """Operator Action 审计资源契约。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None
    actor_id: UUID | None
    action: str = Field(max_length=100)
    resource_type: str = Field(max_length=50)
    resource_id: str | None = Field(default=None, max_length=100)
    workflow_execution_id: UUID | None
    trace_id: str | None = Field(default=None, max_length=64)
    status: str = Field(max_length=20)
    error_code: str | None = Field(default=None, max_length=100)
    metadata_json: dict | None
    created_at: datetime


class OperatorAuditQueryResponse(BaseModel):
    """Operator Action 审计分页响应契约。"""

    items: list[OperatorAuditItem]
    page: int
    page_size: int
    total: int


def _claims(credentials=Depends(bearer)) -> dict:
    """解析当前认证上下文；租户范围只能来自认证 Claims。"""
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _tenant_id(claims: dict) -> UUID:
    """从认证 Claims 取得租户标识。"""
    try:
        return UUID(claims["tenant_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token 缺少有效 tenant_id") from exc


@router.get("", response_model=OperatorAuditQueryResponse)
async def query_operator_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: str | None = Query(None, min_length=9, max_length=100),
    resource_type: str | None = Query(None, min_length=1, max_length=50),
    resource_id: str | None = Query(None, min_length=1, max_length=100),
    actor_id: UUID | None = Query(None),
    status: str | None = Query(None, min_length=1, max_length=20),
    workflow_execution_id: UUID | None = Query(None),
    trace_id: str | None = Query(None, min_length=1, max_length=64),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """分页查询当前租户 Operator Action 审计事实。"""
    try:
        result = await OperatorAuditQueryService(db).query(
            _tenant_id(claims),
            page=page,
            page_size=page_size,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            status=status,
            workflow_execution_id=workflow_execution_id,
            trace_id=trace_id,
            since=since,
            until=until,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result
