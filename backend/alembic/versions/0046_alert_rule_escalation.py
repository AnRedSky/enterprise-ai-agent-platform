"""Phase 2.10-I alert rule escalation configuration."""
from alembic import op
import sqlalchemy as sa

revision = "0046_alert_rule_escalation"
down_revision = "0045_alert_lifecycle_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runtime_alert_rules", sa.Column("escalation", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("runtime_alert_rules", "escalation")
