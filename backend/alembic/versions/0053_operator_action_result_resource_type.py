"""补齐 Operator Action 最终结果资源类型的持久化字段。"""

from alembic import op
import sqlalchemy as sa

revision = "0053_operator_action_result_resource_type"
down_revision = "0052_merge_operator_audit_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为 Operator Action 结果资源增加类型字段，避免结果 ID 承担隐式类型语义。"""
    op.add_column(
        "operator_action_idempotencies",
        sa.Column("result_resource_type", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    """删除 Operator Action 结果资源类型字段。"""
    op.drop_column("operator_action_idempotencies", "result_resource_type")
