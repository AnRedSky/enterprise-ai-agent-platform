"""agent version knowledge configuration

Revision ID: 0009_agent_knowledge_config
Revises: 0008_knowledge_ingestion
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_agent_knowledge_config"
down_revision = "0008_knowledge_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_versions",
        sa.Column("knowledge_config", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("agent_versions", "knowledge_config")
