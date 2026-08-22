import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive

EVENT_METADATA_TYPE = JSON().with_variant(JSONB, "postgresql")


class Execution(Base):
    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_execution_trace_created", "trace_id", "created_at"),
        Index("ix_execution_session_created", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_profile_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="started", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, index=True)


class ExecutionEvent(Base):
    __tablename__ = "execution_events"
    __table_args__ = (Index("ix_execution_event_execution_created", "execution_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    span_type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_profile_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_providers.id", ondelete="SET NULL"), nullable=True, index=True)
    tool_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tools.id", ondelete="SET NULL"), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", EVENT_METADATA_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, index=True)

    def __init__(self, **kwargs: Any) -> None:
        metadata = kwargs.pop("metadata", None)
        super().__init__(**kwargs)
        if metadata is not None:
            self.event_metadata = metadata


ExecutionEvent.metadata = property(lambda self: self.event_metadata)
