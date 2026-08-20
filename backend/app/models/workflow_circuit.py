from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class WorkflowCircuitState(Base):
    __tablename__ = "workflow_circuit_states"
    __table_args__ = (
        UniqueConstraint("tenant_id", "circuit_key", name="uq_workflow_circuit_tenant_key"),
        Index("ix_workflow_circuit_tenant_state", "tenant_id", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    circuit_key: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(20), default="closed", index=True)
    failure_threshold: Mapped[int] = mapped_column(Integer, default=3)
    recovery_timeout_ms: Mapped[int] = mapped_column(Integer, default=10_000)
    half_open_max_calls: Mapped[int] = mapped_column(Integer, default=1)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    half_opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)
