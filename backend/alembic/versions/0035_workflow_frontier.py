"""建立 Durable Workflow Frontier 持久化表。

Revision ID: 0035
Revises: 0034_terminal_execution_releases_worker_lease
"""

from alembic import op
import sqlalchemy as sa


revision = "0035_workflow_frontier"
down_revision = "0034_terminal_execution_releases_worker_lease"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_frontiers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("workflow_version_id", sa.UUID(), nullable=False),
        sa.Column("decision_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("frontier_key", sa.String(length=128), nullable=False),
        sa.Column("node_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("worker_owner", sa.String(length=128), nullable=True),
        sa.Column("worker_lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["execution_id"], ["workflow_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_version_id"], ["workflow_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "frontier_key", name="uq_workflow_frontier_tenant_key"),
    )
    op.create_index("ix_workflow_frontier_tenant_id", "workflow_frontiers", ["tenant_id"])
    op.create_index("ix_workflow_frontier_execution_id", "workflow_frontiers", ["execution_id"])
    op.create_index("ix_workflow_frontier_workflow_version_id", "workflow_frontiers", ["workflow_version_id"])
    op.create_index("ix_workflow_frontier_status", "workflow_frontiers", ["status"])
    op.create_index("ix_workflow_frontier_available_at", "workflow_frontiers", ["available_at"])
    op.create_index("ix_workflow_frontier_claim", "workflow_frontiers", ["tenant_id", "status", "available_at"])
    op.create_index("ix_workflow_frontier_execution_created", "workflow_frontiers", ["tenant_id", "execution_id", "created_at"])
    op.create_index("ix_workflow_frontier_worker_lease", "workflow_frontiers", ["status", "worker_lease_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_workflow_frontier_worker_lease", table_name="workflow_frontiers")
    op.drop_index("ix_workflow_frontier_execution_created", table_name="workflow_frontiers")
    op.drop_index("ix_workflow_frontier_claim", table_name="workflow_frontiers")
    op.drop_index("ix_workflow_frontier_available_at", table_name="workflow_frontiers")
    op.drop_index("ix_workflow_frontier_status", table_name="workflow_frontiers")
    op.drop_index("ix_workflow_frontier_workflow_version_id", table_name="workflow_frontiers")
    op.drop_index("ix_workflow_frontier_execution_id", table_name="workflow_frontiers")
    op.drop_index("ix_workflow_frontier_tenant_id", table_name="workflow_frontiers")
    op.drop_table("workflow_frontiers")
