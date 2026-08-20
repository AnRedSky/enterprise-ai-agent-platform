"""persist circuit breaker policy

Revision ID: 0021_workflow_circuit_policy
Revises: 0020_workflow_circuit_breaker
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_workflow_circuit_policy"
down_revision = "0020_workflow_circuit_breaker"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_circuit_states",
        sa.Column("failure_threshold", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "workflow_circuit_states",
        sa.Column("recovery_timeout_ms", sa.Integer(), nullable=False, server_default="10000"),
    )
    op.add_column(
        "workflow_circuit_states",
        sa.Column("half_open_max_calls", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("workflow_circuit_states", "half_open_max_calls")
    op.drop_column("workflow_circuit_states", "recovery_timeout_ms")
    op.drop_column("workflow_circuit_states", "failure_threshold")
