"""创建 Agent Delegation Durable Entity。

Revision ID: 0038_agent_delegations
Revises: 0037_workflow_node_execution_tenant
"""

from alembic import op
import sqlalchemy as sa

revision = "0038_agent_delegations"
down_revision = "0037_workflow_node_execution_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_delegations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("source_execution_id", sa.UUID(), nullable=False),
        sa.Column("source_agent_version_id", sa.UUID(), nullable=False),
        sa.Column("target_agent_version_id", sa.UUID(), nullable=False),
        sa.Column("delegation_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("selected_context_refs", sa.JSON(), nullable=False),
        sa.Column("allowed_tools", sa.JSON(), nullable=False),
        sa.Column("model_profile_id", sa.UUID(), nullable=True),
        sa.Column("model_budget", sa.JSON(), nullable=False),
        sa.Column("max_delegation_depth", sa.Integer(), nullable=False),
        sa.Column("max_active_delegations", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("worker_execution_id", sa.UUID(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("timeout_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_execution_id"], ["workflow_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_agent_version_id"], ["agent_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_agent_version_id"], ["agent_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_profile_id"], ["model_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["worker_execution_id"], ["workflow_executions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "source_execution_id", "delegation_key", name="uq_agent_delegation_tenant_source_key"),
    )
    op.create_index("ix_agent_delegation_tenant_id", "agent_delegations", ["tenant_id"], unique=False)
    op.create_index("ix_agent_delegation_source_execution_id", "agent_delegations", ["source_execution_id"], unique=False)
    op.create_index("ix_agent_delegation_source_agent_version_id", "agent_delegations", ["source_agent_version_id"], unique=False)
    op.create_index("ix_agent_delegation_target_agent_version_id", "agent_delegations", ["target_agent_version_id"], unique=False)
    op.create_index("ix_agent_delegation_status", "agent_delegations", ["status"], unique=False)
    op.create_index("ix_agent_delegation_source_status", "agent_delegations", ["tenant_id", "source_execution_id", "status"], unique=False)
    op.create_index("ix_agent_delegation_worker_execution", "agent_delegations", ["tenant_id", "worker_execution_id"], unique=False)
    op.create_index("ix_agent_delegation_timeout", "agent_delegations", ["status", "timeout_at"], unique=False)
    op.create_index("ix_agent_delegation_trace_id", "agent_delegations", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_delegation_trace_id", table_name="agent_delegations")
    op.drop_index("ix_agent_delegation_timeout", table_name="agent_delegations")
    op.drop_index("ix_agent_delegation_worker_execution", table_name="agent_delegations")
    op.drop_index("ix_agent_delegation_source_status", table_name="agent_delegations")
    op.drop_index("ix_agent_delegation_status", table_name="agent_delegations")
    op.drop_index("ix_agent_delegation_target_agent_version_id", table_name="agent_delegations")
    op.drop_index("ix_agent_delegation_source_agent_version_id", table_name="agent_delegations")
    op.drop_index("ix_agent_delegation_source_execution_id", table_name="agent_delegations")
    op.drop_index("ix_agent_delegation_tenant_id", table_name="agent_delegations")
    op.drop_table("agent_delegations")
