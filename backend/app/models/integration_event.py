"""Durable Integration Event 持久化模型。

职责：保存企业集成事件及其可靠投递生命周期事实。
边界：不执行投递、不依赖 Redis/MQ；PostgreSQL 是 Durable Event Fact 的唯一事实源。
关键依赖：Tenant 与 SQLAlchemy Base。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class IntegrationEventRecord(Base):
    """可重放、可审计并支持租约投递的 Durable Integration Event。"""

    __tablename__ = "integration_events"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "source", "event_type", "idempotency_key",
            name="uq_integration_event_tenant_source_type_key",
        ),
        Index("ix_integration_event_tenant_status_next", "tenant_id", "status", "next_attempt_at"),
        Index("ix_integration_event_status_next", "status", "next_attempt_at"),
        Index("ix_integration_event_lease", "status", "lease_expires_at"),
        Index("ix_integration_event_subject", "tenant_id", "subject"),
        Index("ix_integration_event_trace", "tenant_id", "trace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive, onupdate=utcnow_naive)
