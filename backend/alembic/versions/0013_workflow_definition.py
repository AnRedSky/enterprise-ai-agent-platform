"""add workflow definition and version tables

Revision ID: 0013_workflow_definition
Revises: 0012_execution_event_metadata
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_workflow_definition"
down_revision = "0012_execution_event_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflows_name", "workflows", ["name"], unique=False)
    op.create_index("ix_workflows_owner_id", "workflows", ["owner_id"], unique=False)
    op.create_index("ix_workflows_status", "workflows", ["status"], unique=False)

    op.create_table(
        "workflow_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id", "version", name="uq_workflow_version"),
    )
    op.create_index("ix_workflow_versions_workflow_id", "workflow_versions", ["workflow_id"], unique=False)
    op.create_index("ix_workflow_versions_created_by", "workflow_versions", ["created_by"], unique=False)
    op.create_index("ix_workflow_versions_status", "workflow_versions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workflow_versions_status", table_name="workflow_versions")
    op.drop_index("ix_workflow_versions_created_by", table_name="workflow_versions")
    op.drop_index("ix_workflow_versions_workflow_id", table_name="workflow_versions")
    op.drop_table("workflow_versions")
    op.drop_index("ix_workflows_status", table_name="workflows")
    op.drop_index("ix_workflows_owner_id", table_name="workflows")
    op.drop_index("ix_workflows_name", table_name="workflows")
    op.drop_table("workflows")
