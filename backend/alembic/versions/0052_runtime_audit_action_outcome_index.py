"""为 Runtime 运维审计动作与结果组合查询补充租户复合索引。"""

from alembic import op

revision = "0052_runtime_audit_action_outcome_index"
down_revision = "0051_runtime_audit_actor_action_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 tenant + action + outcome + created_at 组合查询索引。"""
    op.create_index(
        "ix_runtime_operation_audit_tenant_action_outcome",
        "runtime_operation_audits",
        ["tenant_id", "action", "outcome", "created_at"],
    )


def downgrade() -> None:
    """删除 Runtime 运维审计动作与结果组合查询索引。"""
    op.drop_index(
        "ix_runtime_operation_audit_tenant_action_outcome",
        table_name="runtime_operation_audits",
    )
