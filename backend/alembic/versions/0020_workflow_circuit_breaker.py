"""add workflow circuit breaker persistence

Revision ID: 0020_workflow_circuit_breaker
Revises: 0019_workflow_execution_idempotency
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_workflow_circuit_breaker"
down_revision = "0019_workflow_execution_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_circuit_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("circuit_key", sa.String(length=200), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="closed"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(), nullable=True),
        sa.Column("half_opened_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "circuit_key", name="uq_workflow_circuit_tenant_key"),
    )
    op.create_index("ix_workflow_circuit_states_tenant_id", "workflow_circuit_states", ["tenant_id"])
    op.create_index("ix_workflow_circuit_states_state", "workflow_circuit_states", ["state"])
    op.create_index("ix_workflow_circuit_tenant_state", "workflow_circuit_states", ["tenant_id", "state"])


def downgrade() -> None:
    op.drop_index("ix_workflow_circuit_tenant_state", table_name="workflow_circuit_states")
    op.drop_index("ix_workflow_circuit_states_state", table_name="workflow_circuit_states")
    op.drop_index("ix_workflow_circuit_states_tenant_id", table_name="workflow_circuit_states")
    op.drop_table("workflow_circuit_states")
