"""Workflow Execution Checkpoint 持久化模型。

负责记录 Execution 在关键执行边界上的不可变状态快照，为后续 durable resume 提供持久化基础。
本模块不负责恢复调度、状态机推进或 Worker ownership 校验。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, utcnow_naive


class WorkflowExecutionCheckpoint(Base):
    """Workflow Execution 的不可变检查点快照。"""

    __tablename__ = "workflow_execution_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            "sequence",
            name="uq_workflow_execution_checkpoint_sequence",
        ),
        Index(
            "ix_workflow_execution_checkpoint_execution_created",
            "execution_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    node_attempt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_status: Mapped[str] = mapped_column(String(20))
    node_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    state_data: Mapped[dict] = mapped_column(JSON, default=dict)
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    checkpoint_reason: Mapped[str] = mapped_column(String(50))
    worker_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, index=True)
