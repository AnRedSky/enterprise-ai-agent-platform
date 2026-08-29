"""Webhook destination and subscription persistence models.

职责：保存 tenant-scoped Webhook Destination 与 Event Subscription 配置。
边界：只保存配置事实，不执行 HTTP 投递；Delivery Fact 由 WebhookDelivery 负责。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class WebhookDestination(Base):
    """租户级 Webhook 出站 Destination。"""

    __tablename__ = "webhook_destinations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_webhook_destination_tenant_name"),
        Index("ix_webhook_destination_tenant_enabled", "tenant_id", "enabled"),
        Index("ix_webhook_destination_tenant_provider", "tenant_id", "provider", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="webhook_http")
    endpoint_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    headers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive, onupdate=utcnow_naive
    )


class WebhookSubscription(Base):
    """Event Type → Destination 的 tenant-scoped 订阅映射。"""

    __tablename__ = "webhook_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "destination_id", "event_type", name="uq_webhook_subscription_event"
        ),
        Index("ix_webhook_subscription_tenant_enabled", "tenant_id", "enabled"),
        Index("ix_webhook_subscription_event_type", "tenant_id", "event_type", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("webhook_destinations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(160), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    filter_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive, onupdate=utcnow_naive
    )
