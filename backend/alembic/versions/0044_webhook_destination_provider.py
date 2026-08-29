"""Phase 2.10-I persist provider routing metadata on webhook destinations."""

from alembic import op
import sqlalchemy as sa

revision = "0044_webhook_destination_provider"
down_revision = "0043_webhook_delivery_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "webhook_destinations",
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="webhook_http"),
    )
    op.create_index(
        "ix_webhook_destination_tenant_provider",
        "webhook_destinations",
        ["tenant_id", "provider", "enabled"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_destination_tenant_provider", table_name="webhook_destinations")
    op.drop_column("webhook_destinations", "provider")
