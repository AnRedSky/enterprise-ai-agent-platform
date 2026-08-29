"""Phase 2.9-D Webhook Integration durable facts.

建立 Destination / Subscription / Delivery Fact 三层持久化结构。
Delivery Fact 按 Event × Destination 独立记录，支持后续 fan-out 幂等、Worker lease、retry 与 dead-letter。
"""

from alembic import op
import sqlalchemy as sa

revision = "0042_webhook_delivery_facts"
down_revision = "0041_integration_event_delivery_lease"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_destinations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("endpoint_url", sa.String(length=2048), nullable=False),
        sa.Column("secret_ref", sa.String(length=500), nullable=True),
        sa.Column("headers", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_webhook_destination_tenant_name"),
    )
    op.create_index("ix_webhook_destination_tenant_id", "webhook_destinations", ["tenant_id"])
    op.create_index("ix_webhook_destination_enabled", "webhook_destinations", ["enabled"])
    op.create_index(
        "ix_webhook_destination_tenant_enabled",
        "webhook_destinations",
        ["tenant_id", "enabled"],
    )

    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=160), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("filter_config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["webhook_destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "destination_id", "event_type", name="uq_webhook_subscription_event"
        ),
    )
    op.create_index("ix_webhook_subscription_tenant_id", "webhook_subscriptions", ["tenant_id"])
    op.create_index("ix_webhook_subscription_destination_id", "webhook_subscriptions", ["destination_id"])
    op.create_index("ix_webhook_subscription_enabled", "webhook_subscriptions", ["enabled"])
    op.create_index(
        "ix_webhook_subscription_tenant_enabled",
        "webhook_subscriptions",
        ["tenant_id", "enabled"],
    )
    op.create_index(
        "ix_webhook_subscription_event_type",
        "webhook_subscriptions",
        ["tenant_id", "event_type", "enabled"],
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("integration_event_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["webhook_destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["integration_event_id"], ["integration_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["webhook_subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "destination_id", "integration_event_id",
            name="uq_webhook_delivery_event_destination",
        ),
    )
    op.create_index("ix_webhook_delivery_tenant_id", "webhook_deliveries", ["tenant_id"])
    op.create_index("ix_webhook_delivery_subscription_id", "webhook_deliveries", ["subscription_id"])
    op.create_index("ix_webhook_delivery_destination_id", "webhook_deliveries", ["destination_id"])
    op.create_index("ix_webhook_delivery_integration_event_id", "webhook_deliveries", ["integration_event_id"])
    op.create_index("ix_webhook_delivery_status", "webhook_deliveries", ["status"])
    op.create_index(
        "ix_webhook_delivery_claimable",
        "webhook_deliveries",
        ["tenant_id", "status", "next_attempt_at", "lease_expires_at"],
    )
    op.create_index(
        "ix_webhook_delivery_event",
        "webhook_deliveries",
        ["tenant_id", "integration_event_id"],
    )
    op.create_index(
        "ix_webhook_delivery_destination",
        "webhook_deliveries",
        ["tenant_id", "destination_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_delivery_destination", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_event", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_claimable", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_status", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_integration_event_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_destination_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_subscription_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_tenant_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")

    op.drop_index("ix_webhook_subscription_event_type", table_name="webhook_subscriptions")
    op.drop_index("ix_webhook_subscription_tenant_enabled", table_name="webhook_subscriptions")
    op.drop_index("ix_webhook_subscription_enabled", table_name="webhook_subscriptions")
    op.drop_index("ix_webhook_subscription_destination_id", table_name="webhook_subscriptions")
    op.drop_index("ix_webhook_subscription_tenant_id", table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")

    op.drop_index("ix_webhook_destination_tenant_enabled", table_name="webhook_destinations")
    op.drop_index("ix_webhook_destination_enabled", table_name="webhook_destinations")
    op.drop_index("ix_webhook_destination_tenant_id", table_name="webhook_destinations")
    op.drop_table("webhook_destinations")
