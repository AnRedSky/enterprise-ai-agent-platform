from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class WorkflowSchedule(Base):
    """一个 Scheduled Trigger 对应的持久化调度状态。"""

    __tablename__ = "workflow_schedules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "trigger_id", name="uq_workflow_schedule_tenant_trigger"),
        Index("ix_workflow_schedule_due", "status", "enabled", "next_run_at"),
        Index("ix_workflow_schedule_workflow", "workflow_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    trigger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_triggers.id", ondelete="CASCADE"))
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))
    enabled: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(20), default="enabled", index=True)
    timezone: Mapped[str] = mapped_column(String(64))
    schedule_expression: Mapped[str] = mapped_column(String(255))
    next_run_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    misfire_policy: Mapped[str] = mapped_column(String(20), default="skip")
    catch_up_limit: Mapped[int] = mapped_column(Integer, default=10)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class WorkflowScheduleSlot(Base):
    """Scheduler 槽位的持久化幂等记录，负责最终防止重复创建 WorkflowExecution。"""

    __tablename__ = "workflow_schedule_slots"
    __table_args__ = (
        UniqueConstraint("schedule_slot_key", name="uq_workflow_schedule_slot_key"),
        Index("ix_workflow_schedule_slot_trigger_planned", "trigger_id", "planned_at"),
        Index("ix_workflow_schedule_slot_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    trigger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_triggers.id", ondelete="CASCADE"))
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))
    schedule_slot_key: Mapped[str] = mapped_column(String(255))
    planned_at: Mapped[datetime] = mapped_column(DateTime)
    scheduler_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    workflow_execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
