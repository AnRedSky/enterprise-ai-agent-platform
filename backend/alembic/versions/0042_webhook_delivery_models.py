"""Phase 2.9-D Webhook integration configuration and delivery facts.

职责：建立 Webhook Endpoint、Subscription 与 Delivery 三层持久化模型。
Webhook Delivery 是 Integration Event 的派生投递事实，支持后续独立 Claim、重试与审计。
"""

from alembic import op
import sqlalchemy as sa

revision = "0042_webhook_delivery_models"
down_revision = "0041_integration_event_delivery_lease"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("secret", sa.Text(), nullable=True),
        sa.Column("headers", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_webhook_endpoint_tenant_name"),
    )
    op.create_index(
        "ix_webhook_endpoint_tenant_id", "webhook_endpoints", ["tenant_id"]
    )
    op.create_index(
        "ix_webhook_endpoint_enabled", "webhook_endpoints", ["enabled"]
    )
    op.create_index(
        "ix_webhook_endpoint_tenant_enabled",
        "webhook_endpoints",
        ["tenant_id", "enabled"],
    )

    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("endpoint_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=160), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("filter_config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["endpoint_id"], ["webhook_endpoints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "endpoint_id", "event_type", name="uq_webhook_subscription_event"
        ),
    )
    op.create_index(
        "ix_webhook_subscription_tenant_id", "webhook_subscriptions", ["tenant_id"]
    )
    op.create_index(
        "ix_webhook_subscription_endpoint_id", "webhook_subscriptions", ["endpoint_id"]
    )
    op.create_index(
        "ix_webhook_subscription_enabled", "webhook_subscriptions", ["enabled"]
    )
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
        sa.ForeignKeyConstraint(["integration_event_id"], ["integration_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["webhook_subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "subscription_id", "integration_event_id",
            name="uq_webhook_delivery_event_subscription",
        ),
    )
    op.create_index(
        "ix_webhook_delivery_tenant_id", "webhook_deliveries", ["tenant_id"]
    )
    op.create_index(
        "ix_webhook_delivery_subscription_id", "webhook_deliveries", ["subscription_id"]
    )
    op.create_index(
        "ix_webhook_delivery_integration_event_id",
        "webhook_deliveries",
        ["integration_event_id"],
    )
    op.create_index(
        "ix_webhook_delivery_status", "webhook_deliveries", ["status"]
    )
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


def downgrade() -> None:
    op.drop_index("ix_webhook_delivery_event", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_claimable", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_status", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_integration_event_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_subscription_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_tenant_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")

    op.drop_index("ix_webhook_subscription_event_type", table_name="webhook_subscriptions")
    op.drop_index("ix_webhook_subscription_tenant_enabled", table_name="webhook_subscriptions")
    op.drop_index("ix_webhook_subscription_enabled", table_name="webhook_subscriptions")
    op.drop_index("ix_webhook_subscription_endpoint_id", table_name="webhook_subscriptions")
    op.drop_index("ix_webhook_subscription_tenant_id", table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")

    op.drop_index("ix_webhook_endpoint_tenant_enabled", table_name="webhook_endpoints")
    op.drop_index("ix_webhook_endpoint_enabled", table_name="webhook_endpoints")
    op.drop_index("ix_webhook_endpoint_tenant_id", table_name="webhook_endpoints")
    op.drop_table("webhook_endpoints")
