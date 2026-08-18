"""add persistent memory records

Revision ID: 0002_memory
Revises: 0001_phase_1_2
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_memory"
down_revision = "0001_phase_1_2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "memory_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("memory_type", sa.String(32), nullable=False),
        sa.Column("memory_key", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_memory_user_agent_type", "memory_records", ["user_id", "agent_id", "memory_type"])
    op.create_index("ix_memory_session_created", "memory_records", ["session_id", "created_at"])
    op.create_index("ix_memory_records_user_id", "memory_records", ["user_id"])
    op.create_index("ix_memory_records_agent_id", "memory_records", ["agent_id"])
    op.create_index("ix_memory_records_session_id", "memory_records", ["session_id"])
    op.create_index("ix_memory_records_memory_type", "memory_records", ["memory_type"])
    op.create_index("ix_memory_records_memory_key", "memory_records", ["memory_key"])
    op.create_index("ix_memory_records_created_at", "memory_records", ["created_at"])


def downgrade():
    for name in [
        "ix_memory_records_created_at",
        "ix_memory_records_memory_key",
        "ix_memory_records_memory_type",
        "ix_memory_records_session_id",
        "ix_memory_records_agent_id",
        "ix_memory_records_user_id",
        "ix_memory_session_created",
        "ix_memory_user_agent_type",
    ]:
        op.drop_index(name, table_name="memory_records")
    op.drop_table("memory_records")
