from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ModelUsageRecordResponse(BaseModel):
    id: UUID
    organization_id: UUID
    tenant_id: UUID
    execution_id: UUID | None
    workflow_id: UUID | None
    node_id: str | None
    provider_id: UUID
    profile_id: UUID
    model_type: str
    model_name: str
    request_id: str
    trace_id: str
    outcome: str
    fallback_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    request_units: int
    cost_units: list[str]
    pricing_source: str
    pricing_version: str
    input_cost: Decimal
    output_cost: Decimal
    request_cost: Decimal
    total_cost: Decimal
    created_at: datetime


class ModelUsageListResponse(BaseModel):
    items: list[ModelUsageRecordResponse]
    total: int
    total_cost: Decimal
