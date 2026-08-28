"""为 WorkflowNodeExecution 补齐 tenant durable identity。

Revision ID: 0037_workflow_node_execution_tenant
Revises: 0036_workflow_checkpoint_frontier_binding
"""

from alembic import op
import sqlalchemy as sa

revision = "0037_workflow_node_execution_tenant"
down_revision = "0036_workflow_checkpoint_frontier_binding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_node_executions", sa.Column("tenant_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE workflow_node_executions AS n "
            "SET tenant_id = e.tenant_id "
            "FROM workflow_executions AS e "
            "WHERE e.id = n.execution_id"
        )
    )
    op.alter_column("workflow_node_executions", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_workflow_node_execution_tenant",
        "workflow_node_executions",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_workflow_node_execution_tenant_execution",
        "workflow_node_executions",
        ["tenant_id", "execution_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_node_execution_tenant_execution", table_name="workflow_node_executions")
    op.drop_constraint("fk_workflow_node_execution_tenant", "workflow_node_executions", type_="foreignkey")
    op.drop_column("workflow_node_executions", "tenant_id")
