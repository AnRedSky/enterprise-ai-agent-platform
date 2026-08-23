"""add model usage accounting

Revision ID: 0023_model_usage_accounting
Revises: 0022_workflow_trigger
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_model_usage_accounting"
down_revision = "0022_workflow_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_usage_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=True),
        sa.Column("workflow_id", sa.UUID(), nullable=True),
        sa.Column("node_id", sa.String(length=100), nullable=True),
        sa.Column("provider_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("model_type", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("fallback_reason", sa.String(length=30), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("request_units", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cost_units", sa.JSON(), nullable=False),
        sa.Column("pricing_source", sa.String(length=30), nullable=False),
        sa.Column("pricing_version", sa.String(length=100), nullable=False),
        sa.Column("input_token_rate_per_1k", sa.Numeric(20, 10), nullable=False, server_default="0"),
        sa.Column("output_token_rate_per_1k", sa.Numeric(20, 10), nullable=False, server_default="0"),
        sa.Column("request_rate", sa.Numeric(20, 10), nullable=False, server_default="0"),
        sa.Column("input_cost", sa.Numeric(20, 10), nullable=False, server_default="0"),
        sa.Column("output_cost", sa.Numeric(20, 10), nullable=False, server_default="0"),
        sa.Column("request_cost", sa.Numeric(20, 10), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(20, 10), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["execution_id"], ["workflow_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_id"], ["model_providers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["profile_id"], ["model_profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_model_usage_request_id"),
    )
    op.create_index("ix_model_usage_org_created", "model_usage_records", ["organization_id", "created_at"])
    op.create_index("ix_model_usage_tenant_created", "model_usage_records", ["tenant_id", "created_at"])
    op.create_index("ix_model_usage_execution", "model_usage_records", ["execution_id"])
    op.create_index("ix_model_usage_provider_created", "model_usage_records", ["provider_id", "created_at"])
    op.create_index("ix_model_usage_trace", "model_usage_records", ["trace_id"])
    op.create_index("ix_model_usage_profile_id", "model_usage_records", ["profile_id"])
    op.create_index("ix_model_usage_total_cost", "model_usage_records", ["total_cost"])


def downgrade() -> None:
    op.drop_index("ix_model_usage_total_cost", table_name="model_usage_records")
    op.drop_index("ix_model_usage_profile_id", table_name="model_usage_records")
    op.drop_index("ix_model_usage_trace", table_name="model_usage_records")
    op.drop_index("ix_model_usage_provider_created", table_name="model_usage_records")
    op.drop_index("ix_model_usage_execution", table_name="model_usage_records")
    op.drop_index("ix_model_usage_tenant_created", table_name="model_usage_records")
    op.drop_index("ix_model_usage_org_created", table_name="model_usage_records")
    op.drop_table("model_usage_records")
