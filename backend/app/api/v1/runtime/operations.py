"""Runtime 运维聚合 API 路由。"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims
from app.dependencies.db import get_db
from app.services.integration.webhook_delivery_repository import WebhookDeliveryRepository
from app.services.runtime_operations import RuntimeOperationsEnterpriseService, RuntimeOperationsService, RuntimeProviderHealthService
from app.services.runtime_operations.alerting import RuntimeAlertEvaluator


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


class ProviderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider_type: str = Field(min_length=1, max_length=80)
    config: dict = Field(default_factory=dict)


class ProviderEnabledRequest(BaseModel):
    enabled: bool


class AlertRuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    metric_name: str = Field(min_length=1, max_length=120)
    operator: str
    threshold: float
    window_minutes: int = Field(default=15, ge=1, le=10080)
    severity: str = "warning"
