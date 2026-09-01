"""为 Operator Action 结果关联补充明确的结果资源类型。"""

from alembic import op
import sqlalchemy as sa

revision = "0053_operator_action_result_resource_type"
down_revision = "0052_runtime_audit_action_outcome_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """增加结果资源类型，并修正历史失败记录的伪结果关联。"""
    op.add_column(
        "operator_action_idempotencies",
        sa.Column("result_resource_type", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_operator_action_idempotencies_result_resource_type",
        "operator_action_idempotencies",
        ["result_resource_type"],
    )
    op.create_index(
        "ix_operator_action_result_resource",
        "operator_action_idempotencies",
        ["tenant_id", "result_resource_type", "result_resource_id"],
    )

    op.execute(
        sa.text(
            """
            UPDATE operator_action_idempotencies
            SET result_resource_type = 'workflow_execution'
            WHERE result_resource_id IS NOT NULL
              AND status = 'succeeded'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE operator_action_idempotencies
            SET result_resource_type = NULL,
                result_resource_id = NULL
            WHERE status <> 'succeeded'
              AND result_resource_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    """删除 Operator Action 结果资源类型及其查询索引。"""
    op.drop_index("ix_operator_action_result_resource", table_name="operator_action_idempotencies")
    op.drop_index("ix_operator_action_idempotencies_result_resource_type", table_name="operator_action_idempotencies")
    op.drop_column("operator_action_idempotencies", "result_resource_type")
