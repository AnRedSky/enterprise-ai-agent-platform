"""Immutable audit facts for Webhook Delivery attempts and replay operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class WebhookDeliveryAudit(Base):
    """One immutable audit record per delivery attempt or replay command."""

    __tablename__ = "webhook_delivery_audits"
    __table_args__ = (
        Index("ix_webhook_delivery_audit_tenant_delivery", "tenant_id", "delivery_id", "created_at"),
        Index("ix_webhook_delivery_audit_tenant_event", "tenant_id", "integration_event_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    delivery_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("webhook_deliveries.id", ondelete="CASCADE"), nullable=False, index=True)
    integration_event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("integration_events.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive, index=True)
