"""为 Workflow Execution 增加 Durable Resume 来源与 Checkpoint 关联字段。

Revision ID: 0033
Revises: 0032_workflow_execution_checkpoint
"""

from alembic import op
import sqlalchemy as sa


revision = "0033_workflow_execution_resume_contract"
down_revision = "0032_workflow_execution_checkpoint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """增加 Resume Execution 的来源 Execution 与 Checkpoint 序号字段。"""
    op.add_column(
        "workflow_executions",
        sa.Column("resume_of_execution_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "workflow_executions",
        sa.Column("resume_checkpoint_sequence", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflow_execution_resume_source",
        "workflow_executions",
        "workflow_executions",
        ["resume_of_execution_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_workflow_execution_resume_source",
        "workflow_executions",
        ["resume_of_execution_id", "resume_checkpoint_sequence"],
    )


def downgrade() -> None:
    """删除 Durable Resume 来源与 Checkpoint 关联字段。"""
    op.drop_index("ix_workflow_execution_resume_source", table_name="workflow_executions")
    op.drop_constraint("fk_workflow_execution_resume_source", "workflow_executions", type_="foreignkey")
    op.drop_column("workflow_executions", "resume_checkpoint_sequence")
    op.drop_column("workflow_executions", "resume_of_execution_id")
