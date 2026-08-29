"""Runtime 运维聚合 API 路由。

职责：提供 tenant-scoped Operations Console 所需的指标、SLO 和死信查询接口。
边界：只负责协议、身份与租户上下文适配；不直接修改 Delivery 状态，不执行网络投递。
关键依赖：FastAPI、SQLAlchemy AsyncSession、RuntimeOperationsService。
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims
from app.dependencies.db import get_db
from app.services.runtime_operations import RuntimeOperationsService


class RuntimeOperationsOverview(BaseModel):
    """Runtime 运维聚合指标响应。"""

    window_hours: int
    since: datetime
    generated_at: datetime
    events: dict
    deliveries: dict
    slo: dict


class DeadLetterItem(BaseModel):
    """死信 Delivery 运维记录。"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    integration_event_id: UUID
    destination_id: UUID
    subscription_id: UUID
    status: str
    attempt_count: int
    next_attempt_at: datetime | None = None
    last_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    response_status_code: int | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DeadLetterListResponse(BaseModel):
    """死信分页响应。"""

    items: list[DeadLetterItem]
    page: int
    page_size: int
    total: int


router = APIRouter(prefix="/api/v1/runtime/operations", tags=["runtime-operations"])


def _claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    """解析当前请求认证上下文。"""
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _tenant_id(claims: dict) -> UUID:
    """取得认证上下文中的租户 ID，不接受请求方自行指定租户。"""
    return UUID(claims["tenant_id"])


@router.get("/overview", response_model=RuntimeOperationsOverview)
async def runtime_operations_overview(
    window_hours: int = Query(24, ge=1, le=168),
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """返回当前租户的事件、Delivery、死信和 SLO 聚合指标。"""
    return await RuntimeOperationsService(db).overview(_tenant_id(claims), window_hours=window_hours)


@router.get("/dead-letters", response_model=DeadLetterListResponse)
async def list_dead_letters(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db),
):
    """分页查询当前租户死信 Delivery，查询本身无副作用。"""
    page, page_size, total, rows = await RuntimeOperationsService(db).dead_letters(
        _tenant_id(claims), page=page, page_size=page_size,
    )
    return {"items": rows, "page": page, "page_size": page_size, "total": total}
