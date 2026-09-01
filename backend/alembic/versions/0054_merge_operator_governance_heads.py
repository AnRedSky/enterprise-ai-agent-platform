"""合并 Operator Governance 相关的所有独立 Alembic migration 分支。"""

revision = "0054_merge_operator_governance_heads"
down_revision = (
    "0053_operator_action_result_resource_type",
    "0051_operator_audit_query_indexes",
    "0048_operator_action_audit_lineage",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """合并 Operator Action 结果、Canonical AuditLog 查询与审计关联分支。"""
    pass


def downgrade() -> None:
    """回滚仅撤销 merge 节点，不撤销各父分支已经完成的业务结构。"""
    pass
