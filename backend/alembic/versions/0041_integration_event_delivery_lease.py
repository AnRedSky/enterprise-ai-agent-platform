"""Phase 2.9-C Reliable Event Delivery lease migration。

职责：为 Durable Event 增加 Worker 租约事实，支持崩溃恢复和并发 Claim。
"""

from alembic import op
import sqlalchemy as sa

revision = "0041_integration_event_delivery_lease"
down_revision = "0040_integration_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("integration_events", sa.Column("lease_owner", sa.String(length=128), nullable=True))
    op.add_column("integration_events", sa.Column("lease_expires_at", sa.DateTime(), nullable=True))
    op.create_index("ix_integration_event_lease", "integration_events", ["status", "lease_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_integration_event_lease", table_name="integration_events")
    op.drop_column("integration_events", "lease_expires_at")
    op.drop_column("integration_events", "lease_owner")
