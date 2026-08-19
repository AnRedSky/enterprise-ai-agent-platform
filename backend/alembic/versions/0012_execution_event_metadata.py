"""store structured runtime span metadata for trace/debug correlation

Revision ID: 0012_execution_event_metadata
Revises: 0011_vector_index_status
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_execution_event_metadata"
down_revision = "0011_vector_index_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "execution_events",
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("execution_events", "metadata")
