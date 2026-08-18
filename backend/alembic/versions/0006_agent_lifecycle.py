"""agent publish lifecycle

Revision ID: 0006_agent_lifecycle
Revises: 0005_tool_runtime_integration
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_agent_lifecycle"
down_revision = "0005_tool_runtime_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("published_version_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_agents_published_version",
        "agents",
        "agent_versions",
        ["published_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_agents_published_version", "agents", type_="foreignkey")
    op.drop_column("agents", "published_version_id")
