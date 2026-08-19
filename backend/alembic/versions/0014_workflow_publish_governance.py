"""add workflow published version governance

Revision ID: 0014_workflow_publish_governance
Revises: 0013_workflow_definition
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_workflow_publish_governance"
down_revision = "0013_workflow_definition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("published_version_id", sa.UUID(), nullable=True))
    op.create_index("ix_workflows_published_version_id", "workflows", ["published_version_id"], unique=False)
    op.create_foreign_key(
        "fk_workflows_published_version_id",
        "workflows",
        "workflow_versions",
        ["published_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_workflows_published_version_id", "workflows", type_="foreignkey")
    op.drop_index("ix_workflows_published_version_id", table_name="workflows")
    op.drop_column("workflows", "published_version_id")
