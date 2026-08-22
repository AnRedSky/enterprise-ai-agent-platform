"""Add organization-scoped model provider and model profile governance.

Revision ID: 0025_model_provider_governance
Revises: 0024_embedding_dimension_contract
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_model_provider_governance"
down_revision = "0024_embedding_dimension_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_providers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=True),
        sa.Column("credential_ref", sa.String(length=200), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_model_provider_org_name"),
    )
    op.create_index("ix_model_providers_organization_id", "model_providers", ["organization_id"])
    op.create_index("ix_model_providers_enabled", "model_providers", ["enabled"])

    op.create_table(
        "model_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("model_type", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["model_providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "name", name="uq_model_profile_provider_name"),
    )
    op.create_index("ix_model_profiles_provider_id", "model_profiles", ["provider_id"])
    op.create_index("ix_model_profiles_model_type", "model_profiles", ["model_type"])
    op.create_index("ix_model_profiles_enabled", "model_profiles", ["enabled"])
    op.create_index("ix_model_profiles_is_default", "model_profiles", ["is_default"])


def downgrade() -> None:
    op.drop_index("ix_model_profiles_is_default", table_name="model_profiles")
    op.drop_index("ix_model_profiles_enabled", table_name="model_profiles")
    op.drop_index("ix_model_profiles_model_type", table_name="model_profiles")
    op.drop_index("ix_model_profiles_provider_id", table_name="model_profiles")
    op.drop_table("model_profiles")
    op.drop_index("ix_model_providers_enabled", table_name="model_providers")
    op.drop_index("ix_model_providers_organization_id", table_name="model_providers")
    op.drop_table("model_providers")
