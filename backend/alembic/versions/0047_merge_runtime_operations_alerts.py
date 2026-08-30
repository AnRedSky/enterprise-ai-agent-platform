"""Merge the Runtime Operations and Alert Lifecycle migration branches."""

from alembic import op

revision = "0047_merge_runtime_operations_alerts"
down_revision = ("0044_runtime_operations_enterprise", "0046_alert_rule_escalation")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge-only migration; both parent branches are already applied."""
    pass


def downgrade() -> None:
    """Merge-only migration; downgrade restores the two parent heads."""
    pass
