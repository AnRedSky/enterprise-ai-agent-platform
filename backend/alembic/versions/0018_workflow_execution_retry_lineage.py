"""add workflow execution retry lineage

Revision ID: 0018_workflow_execution_retry_lineage
Revises: 0017_workflow_governance_audit_trace
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_workflow_execution_retry_lineage"
down_revision = "0017_workflow_governance_audit_trace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_executions",
        sa.Column("retry_of_execution_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflow_execution_retry_of",
        "workflow_executions",
        "workflow_executions",
        ["retry_of_execution_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_workflow_executions_retry_of_execution_id",
        "workflow_executions",
        ["retry_of_execution_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_executions_retry_of_execution_id", table_name="workflow_executions")
    op.drop_constraint("fk_workflow_execution_retry_of", "workflow_executions", type_="foreignkey")
    op.drop_column("workflow_executions", "retry_of_execution_id")
