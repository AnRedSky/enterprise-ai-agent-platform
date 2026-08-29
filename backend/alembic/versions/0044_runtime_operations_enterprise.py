"""Phase 2.10-I 运维能力持久化迁移。"""

from alembic import op
import sqlalchemy as sa

revision = "0044_runtime_operations_enterprise"
down_revision = "0043_webhook_delivery_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_provider_registry",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("provider_type", sa.String(length=80), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("health_status", sa.String(length=24), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_runtime_provider_registry_tenant_name"),
    )
    op.create_index("ix_runtime_provider_registry_tenant_enabled", "runtime_provider_registry", ["tenant_id", "enabled"])

    op.create_table(
        "runtime_alert_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("metric_name", sa.String(length=120), nullable=False),
        sa.Column("operator", sa.String(length=8), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="warning"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_runtime_alert_rule_tenant_name"),
    )
    op.create_index("ix_runtime_alert_rule_tenant_enabled", "runtime_alert_rules", ["tenant_id", "enabled"])

    op.create_table(
        "runtime_metric_samples",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("metric_name", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runtime_metric_sample_tenant_metric_time", "runtime_metric_samples", ["tenant_id", "metric_name", "recorded_at"])
    op.create_index("ix_runtime_metric_sample_tenant_time", "runtime_metric_samples", ["tenant_id", "recorded_at"])

    op.create_table(
        "runtime_operation_audits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runtime_operation_audit_tenant_created", "runtime_operation_audits", ["tenant_id", "created_at"])
    op.create_index("ix_runtime_operation_audit_tenant_action", "runtime_operation_audits", ["tenant_id", "action", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_runtime_operation_audit_tenant_action", table_name="runtime_operation_audits")
    op.drop_index("ix_runtime_operation_audit_tenant_created", table_name="runtime_operation_audits")
    op.drop_table("runtime_operation_audits")
    op.drop_index("ix_runtime_metric_sample_tenant_time", table_name="runtime_metric_samples")
    op.drop_index("ix_runtime_metric_sample_tenant_metric_time", table_name="runtime_metric_samples")
    op.drop_table("runtime_metric_samples")
    op.drop_index("ix_runtime_alert_rule_tenant_enabled", table_name="runtime_alert_rules")
    op.drop_table("runtime_alert_rules")
    op.drop_index("ix_runtime_provider_registry_tenant_enabled", table_name="runtime_provider_registry")
    op.drop_table("runtime_provider_registry")
