"""add tenant contract

Revision ID: 0015_tenant_contract
Revises: 0014_workflow_publish_governance
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_tenant_contract"
down_revision = "0014_workflow_publish_governance"
branch_labels = None
depends_on = None

_DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name", name="uq_tenant_name"),
    )
    op.create_index("ix_tenants_name", "tenants", ["name"], unique=False)

    op.execute(
        sa.text(
            "INSERT INTO tenants (id, name, status, created_at) "
            "VALUES (CAST(:id AS UUID), :name, 'active', CURRENT_TIMESTAMP)"
        ).bindparams(id=_DEFAULT_TENANT_ID, name="Default Tenant")
    )

    op.add_column("users", sa.Column("tenant_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text("UPDATE users SET tenant_id = CAST(:tenant_id AS UUID) WHERE tenant_id IS NULL")
        .bindparams(tenant_id=_DEFAULT_TENANT_ID)
    )
    op.alter_column("users", "tenant_id", nullable=False)
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)
    op.create_foreign_key("fk_users_tenant_id", "users", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT")

    op.add_column("workflows", sa.Column("tenant_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE workflows "
            "SET tenant_id = (SELECT tenant_id FROM users WHERE users.id = workflows.owner_id) "
            "WHERE workflows.tenant_id IS NULL"
        )
    )
    op.alter_column("workflows", "tenant_id", nullable=False)
    op.create_index("ix_workflows_tenant_id", "workflows", ["tenant_id"], unique=False)
    op.create_foreign_key("fk_workflows_tenant_id", "workflows", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_workflows_tenant_owner", "workflows", ["tenant_id", "owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workflows_tenant_owner", table_name="workflows")
    op.drop_constraint("fk_workflows_tenant_id", "workflows", type_="foreignkey")
    op.drop_index("ix_workflows_tenant_id", table_name="workflows")
    op.drop_column("workflows", "tenant_id")
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_column("users", "tenant_id")
    op.drop_index("ix_tenants_name", table_name="tenants")
    op.drop_table("tenants")
