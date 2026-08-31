"""为 Runtime 运维审计主体与动作组合查询补充租户复合索引。"""

from alembic import op

revision = "0051_runtime_audit_actor_action_index"
down_revision = "0050_runtime_audit_query_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 tenant + actor + action + created_at 组合查询索引。"""
    op.create_index(
        "ix_runtime_operation_audit_tenant_actor_action",
        "runtime_operation_audits",
        ["tenant_id", "actor", "action", "created_at"],
    )


def downgrade() -> None:
    """删除 Runtime 运维审计主体与动作组合查询索引。"""
    op.drop_index(
        "ix_runtime_operation_audit_tenant_actor_action",
        table_name="runtime_operation_audits",
    )
