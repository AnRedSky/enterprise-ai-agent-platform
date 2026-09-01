"""为 Operator Action 直接审计关联查询补充租户复合索引。"""

from alembic import op

revision = "0055_operator_audit_operator_action_index"
down_revision = "0054_merge_operator_governance_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 tenant + operator_action_id + created_at 组合索引。"""
    op.create_index(
        "ix_operator_audit_tenant_operator_action_created",
        "audit_logs",
        ["tenant_id", "operator_action_id", "created_at"],
    )


def downgrade() -> None:
    """删除 Operator Action 直接审计关联查询索引。"""
    op.drop_index(
        "ix_operator_audit_tenant_operator_action_created",
        table_name="audit_logs",
    )
