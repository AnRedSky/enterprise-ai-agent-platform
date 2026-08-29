"""Runtime 运维企业扩展模型。

职责：持久化 Provider 注册、告警规则、时间序列指标样本、告警生命周期、通知策略与通用运维审计事实。
边界：只保存运维配置与事实，不执行 Provider 网络调用；Secret 只能保存引用，不保存明文凭据。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class RuntimeProviderRegistry(Base):
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


class RuntimeAlertInstance(Base):
    """规则 + routing identity 的持久化告警状态机实例。"""
    __tablename__ = "runtime_alert_instances"
    __table_args__ = (
        UniqueConstraint("tenant_id", "rule_id", "fingerprint", name="uq_runtime_alert_instance_identity"),
        Index("ix_runtime_alert_instance_tenant_state", "tenant_id", "state", "updated_at"),
        Index("ix_runtime_alert_instance_tenant_routing", "tenant_id", "routing_key", "state"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runtime_alert_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="inactive")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="warning")
    routing_key: Mapped[str] = mapped_column(String(160), nullable=False)
    fire_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_fired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_transition: Mapped[str | None] = mapped_column(String(24), nullable=True)
    next_notification_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive, onupdate=utcnow_naive)


class RuntimeNotificationPolicy(Base):
    """租户级通知策略；JSON 仅承载路由配置，不承载 Secret。"""
    __tablename__ = "runtime_notification_policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_runtime_notification_policy_tenant_name"),
        Index("ix_runtime_notification_policy_tenant_enabled", "tenant_id", "enabled"),
        Index("ix_runtime_notification_policy_tenant_severity", "tenant_id", "severity", "enabled"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    routing_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    destination_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    provider_order: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    group_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    escalation: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive, onupdate=utcnow_naive)


class RuntimeNotificationGroup(Base):
    """告警通知聚合窗口。"""
    __tablename__ = "runtime_notification_groups"
    __table_args__ = (
        UniqueConstraint("tenant_id", "group_key", name="uq_runtime_notification_group_identity"),
        Index("ix_runtime_notification_group_tenant_open", "tenant_id", "closed_at", "updated_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    group_key: Mapped[str] = mapped_column(String(256), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    routing_key: Mapped[str] = mapped_column(String(160), nullable=False)
    first_event_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    last_event_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RuntimeNotificationDelivery(Base):
    """Notification transition 到具体 Delivery Fact 的业务审计映射。"""
    __tablename__ = "runtime_notification_deliveries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dedup_key", name="uq_runtime_notification_delivery_dedup"),
        Index("ix_runtime_notification_delivery_tenant_status", "tenant_id", "status", "created_at"),
        Index("ix_runtime_notification_delivery_tenant_group", "tenant_id", "group_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_instance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runtime_alert_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("runtime_notification_groups.id", ondelete="SET NULL"), nullable=True)
    integration_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("integration_events.id", ondelete="SET NULL"), nullable=True, index=True)
    webhook_delivery_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("webhook_deliveries.id", ondelete="SET NULL"), nullable=True, index=True)
    transition: Mapped[str] = mapped_column(String(24), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dedup_key: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_naive, onupdate=utcnow_naive)


class RuntimeMetricSample(Base):
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
