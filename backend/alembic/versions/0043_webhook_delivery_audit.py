"""Phase 2.9-D Webhook Delivery audit facts migration."""

from alembic import op
import sqlalchemy as sa

revision = "0043_webhook_delivery_audit"
down_revision = "0042_webhook_delivery_facts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_delivery_audits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("delivery_id", sa.UUID(), nullable=False),
        sa.Column("integration_event_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["delivery_id"], ["webhook_deliveries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["integration_event_id"], ["integration_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_delivery_audit_tenant", "webhook_delivery_audits", ["tenant_id"])
    op.create_index("ix_webhook_delivery_audit_delivery", "webhook_delivery_audits", ["delivery_id"])
    op.create_index("ix_webhook_delivery_audit_event", "webhook_delivery_audits", ["integration_event_id"])
    op.create_index("ix_webhook_delivery_audit_created", "webhook_delivery_audits", ["created_at"])
    op.create_index(
        "ix_webhook_delivery_audit_tenant_delivery",
        "webhook_delivery_audits",
        ["tenant_id", "delivery_id", "created_at"],
    )
    op.create_index(
        "ix_webhook_delivery_audit_tenant_event",
        "webhook_delivery_audits",
        ["tenant_id", "integration_event_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_delivery_audit_tenant_event", table_name="webhook_delivery_audits")
    op.drop_index("ix_webhook_delivery_audit_tenant_delivery", table_name="webhook_delivery_audits")
    op.drop_index("ix_webhook_delivery_audit_created", table_name="webhook_delivery_audits")
    op.drop_index("ix_webhook_delivery_audit_event", table_name="webhook_delivery_audits")
    op.drop_index("ix_webhook_delivery_audit_delivery", table_name="webhook_delivery_audits")
    op.drop_index("ix_webhook_delivery_audit_tenant", table_name="webhook_delivery_audits")
    op.drop_table("webhook_delivery_audits")
