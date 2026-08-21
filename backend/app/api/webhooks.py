from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.services.webhook_trigger import WebhookTriggerService

router = APIRouter()


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
    execution, created, identity = await service.invoke(
        trigger,
        payload,
        x_webhook_secret,
        idempotency_key,
        request_id,
    )

    # The database uses a bounded, deterministic digest as its durable
    # idempotency key. The public webhook contract must expose the stable,
    # human-auditable identity that the caller supplied, however. Keeping these
    # two representations separate also avoids leaking the internal digest
    # implementation into the HTTP API.
    public_idempotency_key = f"webhook:{trigger.id}:{identity}"

    return JSONResponse(
        status_code=202 if created else 200,
        content={
            "status": "accepted" if created else "duplicate",
            "request_id": request_id,
            "execution_id": str(execution.id),
            "idempotency_key": public_idempotency_key,
        },
    )
