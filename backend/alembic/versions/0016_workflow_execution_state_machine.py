"""add workflow execution state machine

Revision ID: 0016_workflow_execution_state_machine
Revises: 0015_tenant_contract
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_workflow_execution_state_machine"
down_revision = "0015_tenant_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("workflow_version_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("current_node_id", sa.String(100), nullable=True),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workflow_version_id"], ["workflow_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_workflow_executions_tenant_id", "workflow_executions", ["tenant_id"], unique=False)
    op.create_index("ix_workflow_executions_workflow_id", "workflow_executions", ["workflow_id"], unique=False)
    op.create_index("ix_workflow_executions_workflow_version_id", "workflow_executions", ["workflow_version_id"], unique=False)
    op.create_index("ix_workflow_executions_created_by", "workflow_executions", ["created_by"], unique=False)
    op.create_index("ix_workflow_executions_status", "workflow_executions", ["status"], unique=False)
    op.create_index("ix_workflow_executions_created_at", "workflow_executions", ["created_at"], unique=False)
    op.create_index("ix_workflow_execution_tenant_created", "workflow_executions", ["tenant_id", "created_at"], unique=False)
    op.create_index("ix_workflow_execution_workflow_created", "workflow_executions", ["workflow_id", "created_at"], unique=False)

    op.create_table(
        "workflow_node_executions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_data", sa.JSON(), nullable=True),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["workflow_executions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("execution_id", "node_id", name="uq_workflow_node_execution"),
    )
    op.create_index("ix_workflow_node_executions_execution_id", "workflow_node_executions", ["execution_id"], unique=False)
    op.create_index("ix_workflow_node_executions_status", "workflow_node_executions", ["status"], unique=False)
    op.create_index("ix_workflow_node_executions_created_at", "workflow_node_executions", ["created_at"], unique=False)
    op.create_index("ix_workflow_node_execution_execution_created", "workflow_node_executions", ["execution_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workflow_node_execution_execution_created", table_name="workflow_node_executions")
    op.drop_index("ix_workflow_node_executions_created_at", table_name="workflow_node_executions")
    op.drop_index("ix_workflow_node_executions_status", table_name="workflow_node_executions")
    op.drop_index("ix_workflow_node_executions_execution_id", table_name="workflow_node_executions")
    op.drop_table("workflow_node_executions")
    op.drop_index("ix_workflow_execution_workflow_created", table_name="workflow_executions")
    op.drop_index("ix_workflow_execution_tenant_created", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_created_at", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_status", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_created_by", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_workflow_version_id", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_workflow_id", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_tenant_id", table_name="workflow_executions")
    op.drop_table("workflow_executions")
