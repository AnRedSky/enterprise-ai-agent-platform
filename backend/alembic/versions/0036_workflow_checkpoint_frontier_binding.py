"""bind frontier_completed checkpoints to their source frontier

Revision ID: 0036_workflow_checkpoint_frontier_binding
Revises: 0035_workflow_frontier
"""

from alembic import op
import sqlalchemy as sa


revision = "0036_workflow_checkpoint_frontier_binding"
down_revision = "0035_workflow_frontier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_execution_checkpoints",
        sa.Column("frontier_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflow_checkpoint_frontier",
        "workflow_execution_checkpoints",
        "workflow_frontiers",
        ["frontier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_workflow_execution_checkpoint_frontier",
        "workflow_execution_checkpoints",
        ["frontier_id", "checkpoint_reason"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_execution_checkpoint_frontier", table_name="workflow_execution_checkpoints")
    op.drop_constraint("fk_workflow_checkpoint_frontier", "workflow_execution_checkpoints", type_="foreignkey")
    op.drop_column("workflow_execution_checkpoints", "frontier_id")
