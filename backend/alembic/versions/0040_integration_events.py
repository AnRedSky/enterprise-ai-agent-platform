"""Phase 2.9-B Durable Integration Event Persistence migration.

Revision ID: 0040_integration_events
Revises: 0039_workflow_node_execution_tenant_trigger
"""

from alembic import op
import sqlalchemy as sa

revision = "0040_integration_events"
down_revision = "0039_workflow_node_execution_tenant_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=160), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "source", "event_type", "idempotency_key",
            name="uq_integration_event_tenant_source_type_key",
        ),
    )
    op.create_index("ix_integration_events_tenant_id", "integration_events", ["tenant_id"])
    op.create_index("ix_integration_events_event_type", "integration_events", ["event_type"])
    op.create_index("ix_integration_event_tenant_status_next", "integration_events", ["tenant_id", "status", "next_attempt_at"])
    op.create_index("ix_integration_event_status_next", "integration_events", ["status", "next_attempt_at"])
    op.create_index("ix_integration_event_subject", "integration_events", ["tenant_id", "subject"])
    op.create_index("ix_integration_event_trace", "integration_events", ["tenant_id", "trace_id"])
    op.create_index("ix_integration_event_request", "integration_events", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_integration_event_request", table_name="integration_events")
    op.drop_index("ix_integration_event_trace", table_name="integration_events")
    op.drop_index("ix_integration_event_subject", table_name="integration_events")
    op.drop_index("ix_integration_event_status_next", table_name="integration_events")
    op.drop_index("ix_integration_event_tenant_status_next", table_name="integration_events")
    op.drop_index("ix_integration_events_event_type", table_name="integration_events")
    op.drop_index("ix_integration_events_tenant_id", table_name="integration_events")
    op.drop_table("integration_events")
