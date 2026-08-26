"""为 Workflow Execution 增加不可变 Checkpoint 持久化表。

Revision ID: 0032
Revises: 0031_usage_provider_lifecycle
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0032_workflow_execution_checkpoint"
down_revision = "0031_usage_provider_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 Workflow Execution Checkpoint 表。"""
    op.create_table(
        "workflow_execution_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.String(length=100), nullable=True),
        sa.Column("node_attempt", sa.Integer(), nullable=True),
        sa.Column("execution_status", sa.String(length=20), nullable=False),
        sa.Column("node_status", sa.String(length=20), nullable=True),
        sa.Column("state_data", sa.JSON(), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=True),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("checkpoint_reason", sa.String(length=50), nullable=False),
        sa.Column("worker_owner", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["workflow_executions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "execution_id",
            "sequence",
            name="uq_workflow_execution_checkpoint_sequence",
        ),
    )
    op.create_index(
        "ix_workflow_execution_checkpoints_execution_id",
        "workflow_execution_checkpoints",
        ["execution_id"],
    )
    op.create_index(
        "ix_workflow_execution_checkpoint_execution_created",
        "workflow_execution_checkpoints",
        ["execution_id", "created_at"],
    )
    op.create_index(
        "ix_workflow_execution_checkpoints_created_at",
        "workflow_execution_checkpoints",
        ["created_at"],
    )


def downgrade() -> None:
    """删除 Workflow Execution Checkpoint 表。"""
    op.drop_index(
        "ix_workflow_execution_checkpoints_created_at",
        table_name="workflow_execution_checkpoints",
    )
    op.drop_index(
        "ix_workflow_execution_checkpoint_execution_created",
        table_name="workflow_execution_checkpoints",
    )
    op.drop_index(
        "ix_workflow_execution_checkpoints_execution_id",
        table_name="workflow_execution_checkpoints",
    )
    op.drop_table("workflow_execution_checkpoints")
