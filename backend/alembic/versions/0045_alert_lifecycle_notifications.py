"""Phase 2.10-I 告警生命周期与通知编排事实持久化迁移。"""

from alembic import op
import sqlalchemy as sa

revision = "0045_alert_lifecycle_notifications"
# 0045 只沿 Webhook Provider 分支继续，同时声明对 Runtime Operations 分支的
# 强依赖。这样 Alembic 在从 0043 升级时会先完成两个 0044 分支，再创建依赖
# runtime_alert_rules 的告警生命周期表，避免运行时外键引用不存在的表。
down_revision = "0044_webhook_destination_provider"
branch_labels = None
depends_on = "0044_runtime_operations_enterprise"


def upgrade() -> None:
    op.create_table(
        "runtime_alert_instances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("rule_id", sa.UUID(), nullable=False),
        sa.Column("fingerprint", sa.String(128), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("routing_key", sa.String(160), nullable=False),
        sa.Column("fire_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_fired_at", sa.DateTime(), nullable=True),
        sa.Column("last_fired_at", sa.DateTime(), nullable=True),
        sa.Column("recovered_at", sa.DateTime(), nullable=True),
        sa.Column("last_value", sa.Float(), nullable=True),
        sa.Column("last_transition", sa.String(24), nullable=True),
        sa.Column("next_notification_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["runtime_alert_rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "rule_id", "fingerprint", name="uq_runtime_alert_instance_identity"),
    )
    op.create_index("ix_runtime_alert_instance_tenant_state", "runtime_alert_instances", ["tenant_id", "state", "updated_at"])
    op.create_index("ix_runtime_alert_instance_tenant_routing", "runtime_alert_instances", ["tenant_id", "routing_key", "state"])

    op.create_table(
        "runtime_notification_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("severity", sa.String(16), nullable=True),
        sa.Column("routing_key", sa.String(160), nullable=True),
        sa.Column("destination_ids", sa.JSON(), nullable=False),
        sa.Column("provider_order", sa.JSON(), nullable=False),
        sa.Column("group_window_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("escalation", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_runtime_notification_policy_tenant_name"),
    )
    op.create_index("ix_runtime_notification_policy_tenant_enabled", "runtime_notification_policies", ["tenant_id", "enabled"])
    op.create_index("ix_runtime_notification_policy_tenant_severity", "runtime_notification_policies", ["tenant_id", "severity", "enabled"])

    op.create_table(
        "runtime_notification_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("group_key", sa.String(256), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("routing_key", sa.String(160), nullable=False),
        sa.Column("first_event_at", sa.DateTime(), nullable=False),
        sa.Column("last_event_at", sa.DateTime(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "group_key", name="uq_runtime_notification_group_identity"),
    )
    op.create_index("ix_runtime_notification_group_tenant_open", "runtime_notification_groups", ["tenant_id", "closed_at", "last_event_at"])

    op.create_table(
        "runtime_notification_deliveries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("alert_instance_id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=True),
        sa.Column("integration_event_id", sa.UUID(), nullable=True),
        sa.Column("webhook_delivery_id", sa.UUID(), nullable=True),
        sa.Column("transition", sa.String(24), nullable=False),
        sa.Column("provider", sa.String(80), nullable=True),
        sa.Column("dedup_key", sa.String(256), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="planned"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["alert_instance_id"], ["runtime_alert_instances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["runtime_notification_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["integration_event_id"], ["integration_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["webhook_delivery_id"], ["webhook_deliveries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "dedup_key", name="uq_runtime_notification_delivery_dedup"),
    )
    op.create_index("ix_runtime_notification_delivery_tenant_status", "runtime_notification_deliveries", ["tenant_id", "status", "created_at"])
    op.create_index("ix_runtime_notification_delivery_tenant_group", "runtime_notification_deliveries", ["tenant_id", "group_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_runtime_notification_delivery_tenant_group", table_name="runtime_notification_deliveries")
    op.drop_index("ix_runtime_notification_delivery_tenant_status", table_name="runtime_notification_deliveries")
    op.drop_table("runtime_notification_deliveries")
    op.drop_index("ix_runtime_notification_group_tenant_open", table_name="runtime_notification_groups")
    op.drop_table("runtime_notification_groups")
    op.drop_index("ix_runtime_notification_policy_tenant_severity", table_name="runtime_notification_policies")
    op.drop_index("ix_runtime_notification_policy_tenant_enabled", table_name="runtime_notification_policies")
    op.drop_table("runtime_notification_policies")
    op.drop_index("ix_runtime_alert_instance_tenant_routing", table_name="runtime_alert_instances")
    op.drop_index("ix_runtime_alert_instance_tenant_state", table_name="runtime_alert_instances")
    op.drop_table("runtime_alert_instances")
