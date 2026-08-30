"""Add consumer-group isolation to webhook delivery facts."""

from alembic import op
import sqlalchemy as sa

revision = "0048_webhook_delivery_consumer_group"
down_revision = "0047_merge_runtime_operations_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "webhook_deliveries",
        sa.Column("consumer_group", sa.String(length=128), nullable=False, server_default="default"),
    )
    # Replace the pre-existing claim index whose key does not include the worker
    # consumer group. Existing rows remain claimable because the new column has
    # a transactional default of ``default``.
    op.drop_index("ix_webhook_delivery_claimable", table_name="webhook_deliveries")
    op.create_index(
        "ix_webhook_delivery_consumer_group",
        "webhook_deliveries",
        ["tenant_id", "consumer_group", "status"],
    )
    op.create_index(
        "ix_webhook_delivery_claimable_v2",
        "webhook_deliveries",
        ["tenant_id", "consumer_group", "status", "next_attempt_at", "lease_expires_at"],
    )
    op.alter_column("webhook_deliveries", "consumer_group", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_webhook_delivery_claimable_v2", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_delivery_consumer_group", table_name="webhook_deliveries")
    op.drop_column("webhook_deliveries", "consumer_group")
    op.create_index(
        "ix_webhook_delivery_claimable",
        "webhook_deliveries",
        ["tenant_id", "status", "next_attempt_at", "lease_expires_at"],
    )
