"""合并 Operator Action 审计关联与 Canonical AuditLog 查询 migration 分支。"""

from alembic import op

revision = "0052_merge_operator_audit_lineage"
down_revision = (
    "0051_operator_audit_query_indexes",
    "0048_operator_action_audit_lineage",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """合并历史独立的 Operator Action 审计关联分支，使 Alembic 恢复单一 head。"""
    pass


def downgrade() -> None:
    """回滚仅撤销 merge 节点，不撤销两个已完成父分支的业务变更。"""
    pass
