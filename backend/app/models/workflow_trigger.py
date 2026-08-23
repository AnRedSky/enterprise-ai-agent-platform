"""Workflow Trigger ORM 模型：定义可驱动 Workflow 执行的触发器持久化结构。

边界：只负责触发器数据模型与数据库约束，不负责触发执行、调度或 HTTP 协议。
关键依赖：SQLAlchemy ORM 与核心 Tenant / Workflow / User 外键。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class WorkflowTrigger(Base):
    __tablename__ = "workflow_triggers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "workflow_id", "name", name="uq_workflow_trigger_tenant_workflow_name"),
        Index("ix_workflow_trigger_tenant_status", "tenant_id", "status"),
        Index("ix_workflow_trigger_workflow_created", "workflow_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    trigger_type: Mapped[str] = mapped_column(String(30), default="manual")
    status: Mapped[str] = mapped_column(String(20), default="enabled", index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)
