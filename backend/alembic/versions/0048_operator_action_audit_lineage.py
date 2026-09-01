"""建立 Operator Action 与 AuditLog 的正式治理关联。"""

from alembic import op
import sqlalchemy as sa


revision = "0048_operator_action_audit_lineage"
down_revision = "0047_merge_runtime_operations_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为审计事实增加可追溯的 Operator Action 外键，并建立租户查询索引。"""
    op.add_column(
        "audit_logs",
        sa.Column("operator_action_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_audit_logs_operator_action_id",
        "audit_logs",
        "operator_action_idempotencies",
        ["operator_action_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_audit_logs_operator_action",
        "audit_logs",
        ["tenant_id", "operator_action_id", "created_at"],
    )


def downgrade() -> None:
    """移除 Operator Action 与 AuditLog 的正式关联。"""
    op.drop_index("ix_audit_logs_operator_action", table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_operator_action_id", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "operator_action_id")
