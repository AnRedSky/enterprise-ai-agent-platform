from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class ModelUsageRecord(Base):
    """单次受治理 Provider 调用的持久化、租户隔离用量记录。

    模型 Profile 可以在后续生命周期中删除；删除后保留历史调用快照，并将
    `profile_id` 置空，避免历史用量阻止配置生命周期管理。
    """

    __tablename__ = "model_usage_records"
    __table_args__ = (
        Index("ix_model_usage_org_created", "organization_id", "created_at"),
        Index("ix_model_usage_tenant_created", "tenant_id", "created_at"),
        Index("ix_model_usage_execution", "execution_id"),
        Index("ix_model_usage_provider_created", "provider_id", "created_at"),
        Index("ix_model_usage_trace", "trace_id"),
        Index("ix_model_usage_profile_id", "profile_id"),
        Index("ix_model_usage_total_cost", "total_cost"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), index=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), index=True)
    execution_id: Mapped[UUID | None] = mapped_column(ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=True)
    workflow_id: Mapped[UUID | None] = mapped_column(ForeignKey("workflows.id", ondelete="RESTRICT"), nullable=True)
    node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("model_providers.id", ondelete="RESTRICT"), index=True)
    profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_type: Mapped[str] = mapped_column(String(20))
    model_name: Mapped[str] = mapped_column(String(200))
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    outcome: Mapped[str] = mapped_column(String(20), index=True)
    fallback_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_units: Mapped[int] = mapped_column(Integer, default=1)
    cost_units: Mapped[list[str]] = mapped_column(JSON, default=list)
    pricing_source: Mapped[str] = mapped_column(String(30))
    pricing_version: Mapped[str] = mapped_column(String(100))
    input_token_rate_per_1k: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=Decimal("0"))
    output_token_rate_per_1k: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=Decimal("0"))
    request_rate: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=Decimal("0"))
    input_cost: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=Decimal("0"))
    output_cost: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=Decimal("0"))
    request_cost: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=Decimal("0"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, index=True)
