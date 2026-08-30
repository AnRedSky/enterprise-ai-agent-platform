"""Operator Action 幂等事实模型。

职责：持久化需要跨请求保持幂等边界的 Operator Action 请求与结果关联。
边界：不执行任何业务动作；业务生命周期仍由 Workflow / Trigger 领域服务负责。
关键依赖：Tenant、User 与 Workflow Execution 外键。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class OperatorActionIdempotency(Base):
    """记录 Operator Action 的租户级幂等请求及其最终结果。"""

    __tablename__ = "operator_action_idempotencies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_operator_action_tenant_key"),
        Index("ix_operator_action_resource", "tenant_id", "resource_type", "resource_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[uuid.UUID] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(50))
    idempotency_key: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="started", index=True)
    result_resource_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)
