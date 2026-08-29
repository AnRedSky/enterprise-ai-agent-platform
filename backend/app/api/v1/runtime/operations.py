"""Runtime 运维聚合 API 路由。

职责：提供 tenant-scoped Operations Console 所需的指标、SLO、维度、告警和死信接口。
边界：只负责协议、身份与租户上下文适配；不直接执行网络投递。
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims
from app.dependencies.db import get_db
from app.services.integration.webhook_delivery_repository import WebhookDeliveryRepository
from app.services.runtime_operations import RuntimeOperationsService


class RuntimeOperationsOverview(BaseModel):
    window_hours: int
    since: datetime
    generated_at: datetime
    events: dict
    deliveries: dict
    slo: dict


class DeadLetterItem(BaseModel):
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
    items: list[DeadLetterItem]
    page: int
    page_size: int
    total: int


class BatchReplayRequest(BaseModel):
    delivery_ids: list[UUID]


class BatchReplayResponse(BaseModel):
    replayed: list[UUID]
    rejected: list[dict]


router = APIRouter(prefix="/api/v1/runtime/operations", tags=["runtime-operations"])


def _claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _tenant_id(claims: dict) -> UUID:
    return UUID(claims["tenant_id"])


@router.get("/overview", response_model=RuntimeOperationsOverview)
async def runtime_operations_overview(
    window_hours: int = Query(24, ge=1, le=168),
    claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db),
):
    return await RuntimeOperationsService(db).overview(_tenant_id(claims), window_hours=window_hours)


@router.get("/dimensions")
async def runtime_operations_dimensions(
    window_hours: int = Query(24, ge=1, le=168),
    claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db),
):
    return await RuntimeOperationsService(db).dimension_metrics(_tenant_id(claims), window_hours=window_hours)


@router.get("/alerts")
async def runtime_operations_alerts(
    window_hours: int = Query(24, ge=1, le=168),
    claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db),
):
    return await RuntimeOperationsService(db).alerts(_tenant_id(claims), window_hours=window_hours)


@router.get("/dead-letters", response_model=DeadLetterListResponse)
async def list_dead_letters(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db),
):
    page, page_size, total, rows = await RuntimeOperationsService(db).dead_letters(
        _tenant_id(claims), page=page, page_size=page_size,
    )
    return {"items": rows, "page": page, "page_size": page_size, "total": total}


@router.post("/dead-letters/replay", response_model=BatchReplayResponse)
async def batch_replay_dead_letters(
    request: BatchReplayRequest,
    claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db),
):
    """批量将当前租户死信重新入队；每项独立处理，网络投递仍由 Worker 执行。"""
    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="delivery replay requires admin role")
    if not request.delivery_ids or len(request.delivery_ids) > 100:
        raise HTTPException(status_code=422, detail="delivery_ids must contain 1 to 100 items")
    tenant_id = _tenant_id(claims)
    actor = str(UUID(claims["sub"]))
    replayed: list[UUID] = []
    rejected: list[dict] = []
    repository = WebhookDeliveryRepository()
    for delivery_id in dict.fromkeys(request.delivery_ids):
        try:
            record = await repository.replay(db, tenant_id, delivery_id, actor)
        except ValueError as exc:
            await db.rollback()
            rejected.append({"delivery_id": delivery_id, "reason": str(exc)})
            continue
        if record is None:
            rejected.append({"delivery_id": delivery_id, "reason": "delivery not found"})
            continue
        replayed.append(delivery_id)
    await db.commit()
    return {"replayed": replayed, "rejected": rejected}
