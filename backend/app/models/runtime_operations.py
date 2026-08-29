"""Runtime 运维企业扩展模型。

职责：持久化 Provider 注册、告警规则、时间序列指标样本与通用运维审计事实。
边界：只保存运维配置与事实，不执行 Provider 网络调用；Secret 只能保存引用，不保存明文凭据。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class RuntimeProviderRegistry(Base):
    """租户级 Provider 注册表，只保存适配器元数据与非敏感配置。"""

    __tablename__ = "runtime_provider_registry"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_runtime_provider_registry_tenant_name"),
        Index("ix_runtime_provider_registry_tenant_enabled", "tenant_id", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(80), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    health_status: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive, onupdate=utcnow_naive)


class RuntimeAlertRule(Base):
    """租户级确定性告警规则。"""

    __tablename__ = "runtime_alert_rules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_runtime_alert_rule_tenant_name"),
        Index("ix_runtime_alert_rule_tenant_enabled", "tenant_id", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False)
    operator: Mapped[str] = mapped_column(String(8), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    window_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="warning")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive, onupdate=utcnow_naive)


class RuntimeMetricSample(Base):
    """Runtime 时间序列指标样本，维度保存在 JSON 中以支持 Provider/Destination/Event Type 扩展。"""

    __tablename__ = "runtime_metric_samples"
    __table_args__ = (
        Index("ix_runtime_metric_sample_tenant_metric_time", "tenant_id", "metric_name", "recorded_at"),
        Index("ix_runtime_metric_sample_tenant_time", "tenant_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive, index=True)


class RuntimeOperationAudit(Base):
    """通用 Runtime 运维操作审计事实。"""

    __tablename__ = "runtime_operation_audits"
    __table_args__ = (
        Index("ix_runtime_operation_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_runtime_operation_audit_tenant_action", "tenant_id", "action", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
