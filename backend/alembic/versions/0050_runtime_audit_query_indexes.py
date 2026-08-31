"""为 Runtime 运维审计查询补充租户维度复合索引。"""

from alembic import op

revision = "0050_runtime_audit_query_indexes"
down_revision = "0049_operator_action_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建审计查询常用过滤组合的数据库索引。"""
    op.create_index(
        "ix_runtime_operation_audit_tenant_resource",
        "runtime_operation_audits",
        ["tenant_id", "resource_type", "resource_id", "created_at"],
    )
    op.create_index(
        "ix_runtime_operation_audit_tenant_outcome",
        "runtime_operation_audits",
        ["tenant_id", "outcome", "created_at"],
    )
    op.create_index(
        "ix_runtime_operation_audit_tenant_actor",
        "runtime_operation_audits",
        ["tenant_id", "actor", "created_at"],
    )


def downgrade() -> None:
    """删除 Runtime 运维审计查询复合索引。"""
    op.drop_index("ix_runtime_operation_audit_tenant_actor", table_name="runtime_operation_audits")
    op.drop_index("ix_runtime_operation_audit_tenant_outcome", table_name="runtime_operation_audits")
    op.drop_index("ix_runtime_operation_audit_tenant_resource", table_name="runtime_operation_audits")
