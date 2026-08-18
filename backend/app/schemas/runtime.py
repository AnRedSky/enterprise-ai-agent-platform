from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int

class ExecutionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    execution_id: UUID
    request_id: str
    trace_id: str
    session_id: UUID | None = None
    agent_id: UUID | None = None
    agent_version: str | None = None
    model_id: str | None = None
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
    tool_id: UUID | None = None
    error_code: str | None = None

class ExecutionTimelineResponse(BaseModel):
    execution: ExecutionItem
    items: list[ExecutionEventItem]

class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    actor_id: UUID | None = None
    agent_id: UUID | None = None
    tool_id: UUID | None = None
    execution_id: UUID | None = None
    action: str
    status: str
    error_code: str | None = None
    created_at: datetime

class AuditLogListResponse(PageMeta):
    items: list[AuditLogItem]
