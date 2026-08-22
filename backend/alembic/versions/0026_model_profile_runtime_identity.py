"""Add governed model profile identity to agent versions and execution traces.

Revision ID: 0026_model_profile_runtime_identity
Revises: 0025_model_provider_governance
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_model_profile_runtime_identity"
down_revision = "0025_model_provider_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_versions", sa.Column("model_profile_id", sa.UUID(), nullable=True))
    op.create_index("ix_agent_versions_model_profile_id", "agent_versions", ["model_profile_id"])
    op.create_foreign_key(
        "fk_agent_versions_model_profile_id",
        "agent_versions",
        "model_profiles",
        ["model_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("executions", sa.Column("model_profile_id", sa.UUID(), nullable=True))
    op.create_index("ix_executions_model_profile_id", "executions", ["model_profile_id"])
    op.create_foreign_key(
        "fk_executions_model_profile_id",
        "executions",
        "model_profiles",
        ["model_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("execution_events", sa.Column("model_profile_id", sa.UUID(), nullable=True))
    op.add_column("execution_events", sa.Column("provider_id", sa.UUID(), nullable=True))
    op.create_index("ix_execution_events_model_profile_id", "execution_events", ["model_profile_id"])
    op.create_index("ix_execution_events_provider_id", "execution_events", ["provider_id"])
    op.create_foreign_key(
        "fk_execution_events_model_profile_id",
        "execution_events",
        "model_profiles",
        ["model_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_execution_events_provider_id",
        "execution_events",
        "model_providers",
        ["provider_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_execution_events_provider_id", "execution_events", type_="foreignkey")
    op.drop_constraint("fk_execution_events_model_profile_id", "execution_events", type_="foreignkey")
    op.drop_index("ix_execution_events_provider_id", table_name="execution_events")
    op.drop_index("ix_execution_events_model_profile_id", table_name="execution_events")
    op.drop_column("execution_events", "provider_id")
    op.drop_column("execution_events", "model_profile_id")

    op.drop_constraint("fk_executions_model_profile_id", "executions", type_="foreignkey")
    op.drop_index("ix_executions_model_profile_id", table_name="executions")
    op.drop_column("executions", "model_profile_id")

    op.drop_constraint("fk_agent_versions_model_profile_id", "agent_versions", type_="foreignkey")
    op.drop_index("ix_agent_versions_model_profile_id", table_name="agent_versions")
    op.drop_column("agent_versions", "model_profile_id")
