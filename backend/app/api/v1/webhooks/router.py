from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims
from app.dependencies.db import get_db
from app.schemas.webhook_integration import (
    WebhookDestinationCreate,
    WebhookDestinationResponse,
    WebhookFanoutResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse,
)
from app.services.integration.webhook import WebhookIntegrationService
from app.services.trigger import WebhookTriggerService

router = APIRouter()


def _tenant_id(claims: dict) -> UUID:
    raw = claims.get("tenant_id")
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前 Token 未绑定 tenant_id")
    try:
        return UUID(str(raw))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token tenant_id 无效") from exc


@router.get("/destinations", response_model=list[WebhookDestinationResponse])
async def list_destinations(
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    return await WebhookIntegrationService(db).list_destinations(_tenant_id(claims))


@router.post("/destinations", response_model=WebhookDestinationResponse, status_code=201)
async def create_destination(
    payload: WebhookDestinationCreate,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await WebhookIntegrationService(db).create_destination(
            tenant_id=_tenant_id(claims),
            name=payload.name,
            endpoint_url=str(payload.endpoint_url),
            secret_ref=payload.secret_ref,
            headers=payload.headers,
        )
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Destination 创建失败，可能已存在同名 Destination") from exc


@router.get("/subscriptions", response_model=list[WebhookSubscriptionResponse])
async def list_subscriptions(
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    return await WebhookIntegrationService(db).list_subscriptions(_tenant_id(claims))


@router.post("/subscriptions", response_model=WebhookSubscriptionResponse, status_code=201)
async def create_subscription(
    payload: WebhookSubscriptionCreate,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await WebhookIntegrationService(db).create_subscription(
            tenant_id=_tenant_id(claims),
            destination_id=payload.destination_id,
            event_type=payload.event_type,
            priority=payload.priority,
            filter_config=payload.filter_config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Subscription 创建失败，可能已存在相同 Event Type 订阅") from exc


@router.post("/events/{event_id}/fanout", response_model=WebhookFanoutResponse)
async def plan_webhook_fanout(
    event_id: UUID,
    claims: dict = Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    try:
        planned = await WebhookIntegrationService(db).plan_fanout(_tenant_id(claims), event_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WebhookFanoutResponse(event_id=event_id, planned=planned)


@router.post("/{trigger_id}")
async def receive_webhook(
    trigger_id: UUID,
    payload: dict,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=100),
    request_id: str | None = Header(default=None, alias="X-Request-ID", max_length=100),
    db: AsyncSession = Depends(get_db),
):
    request_id = request_id or str(uuid.uuid4())
    service = WebhookTriggerService(db)
    trigger = await service.get_trigger(trigger_id)
    execution, created, _ = await service.invoke(
        trigger,
        payload,
        x_webhook_secret,
        idempotency_key,
        request_id,
    )

    return JSONResponse(
        status_code=202 if created else 200,
        content={
            "status": "accepted" if created else "duplicate",
            "request_id": request_id,
            "execution_id": str(execution.id),
            "idempotency_key": execution.idempotency_key,
        },
    )
