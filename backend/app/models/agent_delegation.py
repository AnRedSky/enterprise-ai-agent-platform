"""Agent Delegation Durable Entity。

职责：持久化一次受治理的跨 Agent 子任务委派及其生命周期、预算、上下文与 lineage。
边界：不执行 Worker Runtime，不复制 Workflow Execution 的 retry/recovery 状态机。
关键依赖：Tenant、WorkflowExecution、AgentVersion 以及 PostgreSQL 唯一约束。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class AgentDelegation(Base):
    """受治理 Agent Delegation 的 Durable 状态模型。"""

    __tablename__ = "agent_delegations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_execution_id", "delegation_key", name="uq_agent_delegation_tenant_source_key"),
        Index("ix_agent_delegation_source_status", "tenant_id", "source_execution_id", "status"),
        Index("ix_agent_delegation_worker_execution", "tenant_id", "worker_execution_id"),
        Index("ix_agent_delegation_timeout", "status", "timeout_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), index=True)
    source_execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_executions.id", ondelete="CASCADE"), index=True)
    source_agent_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_versions.id", ondelete="RESTRICT"), index=True)
    target_agent_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_versions.id", ondelete="RESTRICT"), index=True)
    delegation_key: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    selected_context_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    allowed_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    model_profile_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    model_budget: Mapped[dict] = mapped_column(JSON, default=dict)
    max_delegation_depth: Mapped[int] = mapped_column(Integer)
    max_active_delegations: Mapped[int] = mapped_column(Integer)
    timeout_seconds: Mapped[int] = mapped_column(Integer)
    depth: Mapped[int] = mapped_column(Integer, default=1)
    worker_execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    timeout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
