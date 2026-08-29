from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class WebhookDestinationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    endpoint_url: HttpUrl
    secret_ref: str | None = Field(default=None, max_length=500)
    headers: dict[str, str] = Field(default_factory=dict)


class WebhookDestinationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    endpoint_url: str
    secret_ref: str | None
    headers: dict[str, str]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookSubscriptionCreate(BaseModel):
    destination_id: UUID
    event_type: str = Field(min_length=1, max_length=160)
    priority: int = Field(default=100, ge=0, le=10000)
    filter_config: dict = Field(default_factory=dict)


class WebhookSubscriptionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    destination_id: UUID
    event_type: str
    priority: int
    enabled: bool
    filter_config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookFanoutResponse(BaseModel):
    event_id: UUID
    planned: int
