"""add organization and membership governance domain

Revision ID: 0023_organization_membership
Revises: 0022_workflow_trigger
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_organization_membership"
down_revision = "0022_workflow_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_organization_tenant_id", "organizations", ["tenant_id"])
    op.create_index("ix_organization_name", "organizations", ["name"])
    op.create_index("ix_organization_status", "organizations", ["status"])

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_membership_org_user"),
    )
    op.create_index("ix_organization_membership_organization_id", "organization_memberships", ["organization_id"])
    op.create_index("ix_organization_membership_user_id", "organization_memberships", ["user_id"])
    op.create_index("ix_organization_membership_status", "organization_memberships", ["status"])
    op.create_index("ix_organization_membership_role", "organization_memberships", ["role"])

    # Organization is a product-level 1:1 projection of the existing tenant boundary.
    op.execute(sa.text("""
        INSERT INTO organizations (id, tenant_id, name, status, created_at, updated_at)
        SELECT gen_random_uuid(), t.id, t.name, t.status, t.created_at, t.created_at
        FROM tenants AS t
    """))

    # Preserve existing RBAC semantics during migration. The first existing admin
    # in a tenant becomes owner; additional admins remain organization admins.
    # All other users become members. Ordering is deterministic for repeatable audit.
    op.execute(sa.text("""
        WITH admin_candidates AS (
            SELECT
                u.id AS user_id,
                u.tenant_id,
                row_number() OVER (
                    PARTITION BY u.tenant_id
                    ORDER BY u.created_at ASC, u.id ASC
                ) AS admin_rank
            FROM users AS u
            JOIN user_roles AS ur ON ur.user_id = u.id
            JOIN roles AS r ON r.id = ur.role_id
            WHERE r.name = 'admin'
        )
        INSERT INTO organization_memberships (
            id, organization_id, user_id, status, role, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            o.id,
            u.id,
            CASE WHEN u.status = 'active' THEN 'active' ELSE 'suspended' END,
            CASE
                WHEN ac.admin_rank = 1 THEN 'owner'
                WHEN ac.admin_rank IS NOT NULL THEN 'admin'
                ELSE 'member'
            END,
            u.created_at,
            u.created_at
        FROM users AS u
        JOIN organizations AS o ON o.tenant_id = u.tenant_id
        LEFT JOIN admin_candidates AS ac ON ac.user_id = u.id
    """))


def downgrade() -> None:
    op.drop_index("ix_organization_membership_role", table_name="organization_memberships")
    op.drop_index("ix_organization_membership_status", table_name="organization_memberships")
    op.drop_index("ix_organization_membership_user_id", table_name="organization_memberships")
    op.drop_index("ix_organization_membership_organization_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_index("ix_organization_status", table_name="organizations")
    op.drop_index("ix_organization_name", table_name="organizations")
    op.drop_index("ix_organization_tenant_id", table_name="organizations")
    op.drop_table("organizations")
