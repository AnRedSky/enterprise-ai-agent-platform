"""Webhook delivery lifecycle model.

职责：为每个 Durable Integration Event × Webhook Destination 保存独立投递事实。
边界：不执行网络请求；Worker 根据此模型进行 Claim、lease、retry 和 dead-letter。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class WebhookDelivery(Base):
    """单个 Destination 的可靠 Webhook 投递事实。"""

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "destination_id", "integration_event_id",
            name="uq_webhook_delivery_event_destination",
        ),
        Index(
            "ix_webhook_delivery_claimable",
            "tenant_id", "status", "next_attempt_at", "lease_expires_at",
        ),
        Index("ix_webhook_delivery_event", "tenant_id", "integration_event_id"),
        Index("ix_webhook_delivery_destination", "tenant_id", "destination_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("webhook_destinations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    integration_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("integration_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive, onupdate=utcnow_naive
    )
