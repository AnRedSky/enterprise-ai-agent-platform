"""add memory governance fields

Revision ID: 0003_memory_governance
Revises: 0002_memory
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_memory_governance"
down_revision = "0002_memory"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("memory_records", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("memory_records", sa.Column("expires_at", sa.DateTime(), nullable=True))
    op.create_index("ix_memory_active_expires", "memory_records", ["is_active", "expires_at"])


def downgrade():
    op.drop_index("ix_memory_active_expires", table_name="memory_records")
    op.drop_column("memory_records", "expires_at")
    op.drop_column("memory_records", "is_active")
