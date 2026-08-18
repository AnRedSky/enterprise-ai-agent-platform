"""add observability execution tables

Revision ID: 0004_observability
Revises: 0003_memory_governance
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_observability"
down_revision = "0003_memory_governance"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("agent_version", sa.String(length=32), nullable=True),
        sa.Column("model_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_executions_request_id", "executions", ["request_id"])
    op.create_index("ix_executions_trace_id", "executions", ["trace_id"])
    op.create_index("ix_execution_trace_created", "executions", ["trace_id", "created_at"], unique=False)
    op.create_index("ix_execution_session_created", "executions", ["session_id", "created_at"], unique=False)
    op.create_index("ix_executions_status", "executions", ["status"])

    op.create_table(
        "execution_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("span_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("model_id", sa.String(length=100), nullable=True),
        sa.Column("tool_id", sa.Uuid(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_events_execution_id", "execution_events", ["execution_id"])
    op.create_index("ix_execution_events_trace_id", "execution_events", ["trace_id"])
    op.create_index("ix_execution_events_span_type", "execution_events", ["span_type"])
    op.create_index("ix_execution_event_execution_created", "execution_events", ["execution_id", "created_at"])
    op.create_index("ix_execution_events_created_at", "execution_events", ["created_at"])


def downgrade():
    op.drop_table("execution_events")
    op.drop_table("executions")
