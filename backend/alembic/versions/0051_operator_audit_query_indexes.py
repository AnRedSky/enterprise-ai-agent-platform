"""为 Canonical Operator Audit 查询补充 AuditLog 租户复合索引。"""

from alembic import op

revision = "0051_operator_audit_query_indexes"
down_revision = "0050_runtime_audit_query_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为当前 OperatorAuditQueryService 的实际事实源 AuditLog 建立租户查询索引。

    0050 仍保留历史 Runtime Operation Audit 表的索引；当前 Operator Audit
    已统一以 audit_logs 为唯一事实源，因此不能依赖旧表索引承担查询性能。
    """
    op.create_index(
        "ix_operator_audit_tenant_action_created",
        "audit_logs",
        ["tenant_id", "action", "created_at"],
    )
    op.create_index(
        "ix_operator_audit_tenant_actor_created",
        "audit_logs",
        ["tenant_id", "actor_id", "created_at"],
    )
    op.create_index(
        "ix_operator_audit_tenant_resource_created",
        "audit_logs",
        ["tenant_id", "resource_type", "resource_id", "created_at"],
    )
    op.create_index(
        "ix_operator_audit_tenant_execution_created",
        "audit_logs",
        ["tenant_id", "workflow_execution_id", "created_at"],
    )
    op.create_index(
        "ix_operator_audit_tenant_trace_created",
        "audit_logs",
        ["tenant_id", "trace_id", "created_at"],
    )


def downgrade() -> None:
    """删除 Canonical Operator Audit 查询复合索引。"""
    op.drop_index("ix_operator_audit_tenant_trace_created", table_name="audit_logs")
    op.drop_index("ix_operator_audit_tenant_execution_created", table_name="audit_logs")
    op.drop_index("ix_operator_audit_tenant_resource_created", table_name="audit_logs")
    op.drop_index("ix_operator_audit_tenant_actor_created", table_name="audit_logs")
    op.drop_index("ix_operator_audit_tenant_action_created", table_name="audit_logs")
