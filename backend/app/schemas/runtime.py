from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int


class ExecutionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    execution_id: UUID = Field(validation_alias=AliasChoices("execution_id", "id"))
    request_id: str
    trace_id: str
    session_id: UUID | None = None
    agent_id: UUID | None = None
    agent_version: str | None = None
    model_id: str | None = None
    model_profile_id: UUID | None = None
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = None
    error_code: str | None = None


class ExecutionListResponse(PageMeta):
    items: list[ExecutionItem]


class ExecutionEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    execution_id: UUID
    trace_id: str
    span_type: str
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = None
    model_id: str | None = None
    model_profile_id: UUID | None = None
    provider_id: UUID | None = None
    tool_id: UUID | None = None
    error_code: str | None = None
    metadata: dict[str, Any] | None = None


class ExecutionTimelineResponse(BaseModel):
    execution: ExecutionItem
    items: list[ExecutionEventItem]


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    agent_id: UUID | None = None
    tool_id: UUID | None = None
    workflow_id: UUID | None = None
    workflow_version_id: UUID | None = None
    workflow_execution_id: UUID | None = None
    execution_id: UUID | None = None
    action: str
    status: str
    error_code: str | None = None
    metadata_json: dict[str, Any] | None = Field(default=None, validation_alias=AliasChoices("metadata_json", "metadata"))
    created_at: datetime


class AuditLogListResponse(PageMeta):
    items: list[AuditLogItem]


class WorkflowTraceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    execution_id: UUID
    workflow_id: UUID
    workflow_version_id: UUID
    node_id: str | None = None
    event_type: str
    status: str
    trace_id: str
    actor_id: UUID | None = None
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime


class WorkflowTraceResponse(BaseModel):
    execution_id: UUID
    items: list[WorkflowTraceItem]


class IntegrationEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    event_type: str
    schema_version: int
    source: str
    subject: str
    idempotency_key: str
    occurred_at: datetime
    request_id: str | None = None
    trace_id: str | None = None
    payload: dict[str, Any]
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    status: str
    attempt_count: int
    next_attempt_at: datetime | None = None
    last_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    last_error_code: str | None = None
    created_at: datetime


class IntegrationEventListResponse(PageMeta):
    items: list[IntegrationEventItem]


class IntegrationEventSummaryResponse(BaseModel):
    """当前租户 Integration Event 的运维聚合结果。"""

    total: int
    status_counts: dict[str, int]
    source_counts: dict[str, int]
    generated_at: datetime


class IntegrationEventDeliveryItem(BaseModel):
    """Integration Event 对应的 Webhook Delivery 运维事实。"""

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


class IntegrationEventDeliveryListResponse(PageMeta):
    items: list[IntegrationEventDeliveryItem]
