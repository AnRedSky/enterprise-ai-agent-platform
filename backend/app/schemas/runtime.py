from datetime import datetime
from typing import Any
from uuid import UUID
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
    operator_action_id: UUID | None = None
    execution_id: UUID | None = None
    resource_type: str
    resource_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
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


class WebhookDeliveryAuditItem(BaseModel):
    """Webhook Delivery replay/attempt 的不可变运维审计事实。"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    delivery_id: UUID
    integration_event_id: UUID
    action: str
    attempt_count: int
    status: str
    response_status_code: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    actor: str
    created_at: datetime


class WebhookDeliveryAuditListResponse(PageMeta):
    items: list[WebhookDeliveryAuditItem]


class IntegrationEventReplayResponse(BaseModel):
    """Replay 操作后的 Delivery 状态。"""

    delivery: IntegrationEventDeliveryItem
    replayed: bool = True


class RuntimeWorkerOwner(BaseModel):
    """Worker Durable claim owner 聚合。"""

    worker_owner: str
    claim_count: int


class RuntimeWorkerError(BaseModel):
    """Worker Frontier 最近错误事实。"""

    id: UUID
    execution_id: UUID
    status: str
    attempt: int
    worker_owner: str | None = None
    worker_lease_expires_at: datetime | None = None
    error_code: str
    created_at: datetime


class RuntimeWorkerDiagnosticsResponse(BaseModel):
    """Worker claim / lease / owner 只读诊断 Contract。"""

    window_hours: int
    generated_at: datetime
    liveness: str
    liveness_reason_code: str
    frontier: dict[str, Any]
    leases: dict[str, int]
    owners: list[RuntimeWorkerOwner]
    recent_errors: list[RuntimeWorkerError]


class RuntimeSchedulerTrigger(BaseModel):
    """Scheduler scheduled trigger 的 Durable 配置摘要。"""

    id: UUID
    workflow_id: UUID
    name: str
    status: str
    config: dict[str, Any]
    updated_at: datetime


class RuntimeSchedulerDiagnosticsResponse(BaseModel):
    """Scheduler Durable backlog 与 trigger 状态只读诊断 Contract。"""

    generated_at: datetime
    liveness: str
    liveness_reason_code: str
    durable: dict[str, int]
    triggers: list[RuntimeSchedulerTrigger]


class RuntimeCorrelationExecution(BaseModel):
    """Audit / Trace 关联视图中的 Workflow Execution 最小事实。"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    workflow_id: UUID
    workflow_version_id: UUID
    created_by: UUID
    retry_of_execution_id: UUID | None = None
    resume_of_execution_id: UUID | None = None
    status: str
    current_node_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime


class RuntimeOperatorActionItem(BaseModel):
    """关联视图中的 Operator Action 幂等事实。"""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    actor_id: UUID
    resource_type: str
    resource_id: UUID
    action: str
    idempotency_key: str
    status: str
    result_resource_type: str | None = None
    result_resource_id: UUID | None = None
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class RuntimeCorrelationPage(BaseModel):
    """关联 Trace / Audit 集合的稳定分页元数据。"""

    page: int
    page_size: int
    total: int


class RuntimeCorrelationTracePage(RuntimeCorrelationPage):
    """关联视图中的 Trace 分页集合。"""

    items: list[WorkflowTraceItem]


class RuntimeCorrelationAuditPage(RuntimeCorrelationPage):
    """关联视图中的 Audit 分页集合。"""

    items: list[AuditLogItem]


class RuntimeCorrelationResponse(BaseModel):
    """Execution、Trace、Audit 与 Operator Action 双向关联 Contract。"""

    execution: RuntimeCorrelationExecution | None
    traces: RuntimeCorrelationTracePage
    audits: RuntimeCorrelationAuditPage
    operator_actions: list[RuntimeOperatorActionItem]
    focused_traces: list[WorkflowTraceItem] = Field(default_factory=list)
    focused_audit: AuditLogItem | None = None
    focus_audit_id: UUID | None = None
    focus_operator_action_id: UUID | None = None
