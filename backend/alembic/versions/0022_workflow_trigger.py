"""add workflow trigger contract

Revision ID: 0022_workflow_trigger
Revises: 0021_workflow_circuit_policy
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_workflow_trigger"
down_revision = "0021_workflow_circuit_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_triggers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "workflow_id", "name", name="uq_workflow_trigger_tenant_workflow_name"),
    )
    op.create_index("ix_workflow_trigger_tenant_id", "workflow_triggers", ["tenant_id"])
    op.create_index("ix_workflow_trigger_workflow_id", "workflow_triggers", ["workflow_id"])
    op.create_index("ix_workflow_trigger_created_by", "workflow_triggers", ["created_by"])
    op.create_index("ix_workflow_trigger_status", "workflow_triggers", ["status"])
    op.create_index("ix_workflow_trigger_tenant_status", "workflow_triggers", ["tenant_id", "status"])
    op.create_index("ix_workflow_trigger_workflow_created", "workflow_triggers", ["workflow_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_workflow_trigger_workflow_created", table_name="workflow_triggers")
    op.drop_index("ix_workflow_trigger_tenant_status", table_name="workflow_triggers")
    op.drop_index("ix_workflow_trigger_status", table_name="workflow_triggers")
    op.drop_index("ix_workflow_trigger_created_by", table_name="workflow_triggers")
    op.drop_index("ix_workflow_trigger_workflow_id", table_name="workflow_triggers")
    op.drop_index("ix_workflow_trigger_tenant_id", table_name="workflow_triggers")
    op.drop_table("workflow_triggers")
