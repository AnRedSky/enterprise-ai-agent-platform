"""合并历史 AuditLog 分支与当前 Operator Governance migration head。"""

from alembic import op


revision = "0056_merge_legacy_audit_and_operator_governance_heads"
down_revision = (
    "0055_operator_audit_operator_action_index",
    "0013_remove_legacy_audit_execution_fk",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """合并历史 audit execution 外键修复分支，形成唯一 Alembic head。"""
    pass


def downgrade() -> None:
    """回滚仅撤销 merge 节点，不撤销两个父分支已经完成的业务结构。"""
    pass
