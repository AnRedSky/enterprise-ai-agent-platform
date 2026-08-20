"""add workflow execution idempotency key

Revision ID: 0019_workflow_execution_idempotency
Revises: 0018_workflow_execution_retry_lineage
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_workflow_execution_idempotency"
down_revision = "0018_workflow_execution_retry_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_executions",
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
    )
    op.create_unique_constraint(
        "uq_workflow_execution_tenant_idempotency",
        "workflow_executions",
        ["tenant_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_workflow_execution_tenant_idempotency", "workflow_executions", type_="unique")
    op.drop_column("workflow_executions", "idempotency_key")
