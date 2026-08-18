"""tool runtime integration audit fields

Revision ID: 0005_tool_runtime_integration
Revises: 0004_observability
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_tool_runtime_integration"
down_revision = "0004_observability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tools", sa.Column("input_schema", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("agent_tools", sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("audit_logs", sa.Column("agent_id", sa.UUID(), nullable=True))
    op.add_column("audit_logs", sa.Column("tool_id", sa.UUID(), nullable=True))
    op.add_column("audit_logs", sa.Column("execution_id", sa.UUID(), nullable=True))
    op.add_column("audit_logs", sa.Column("status", sa.String(length=20), nullable=False, server_default="success"))
    op.add_column("audit_logs", sa.Column("error_code", sa.String(length=100), nullable=True))
    op.add_column("audit_logs", sa.Column("metadata", sa.JSON(), nullable=True))
    op.create_foreign_key("fk_audit_agent", "audit_logs", "agents", ["agent_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_audit_tool", "audit_logs", "tools", ["tool_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_audit_execution", "audit_logs", "executions", ["execution_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_audit_execution", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_tool", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_agent", "audit_logs", type_="foreignkey")
    for table, column in (("audit_logs", "metadata"), ("audit_logs", "error_code"), ("audit_logs", "status"), ("audit_logs", "execution_id"), ("audit_logs", "tool_id"), ("audit_logs", "agent_id"), ("agent_tools", "enabled"), ("tools", "input_schema")):
        op.drop_column(table, column)
