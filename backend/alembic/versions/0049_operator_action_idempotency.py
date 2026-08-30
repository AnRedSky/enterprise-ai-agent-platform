"""Create tenant-scoped Operator Action idempotency facts."""

from alembic import op
import sqlalchemy as sa

revision = "0049_operator_action_idempotency"
down_revision = "0048_webhook_delivery_consumer_group"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operator_action_idempotencies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="started"),
        sa.Column("result_resource_id", sa.UUID(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_operator_action_tenant_key"),
    )
    op.create_index("ix_operator_action_idempotencies_tenant_id", "operator_action_idempotencies", ["tenant_id"])
    op.create_index("ix_operator_action_idempotencies_actor_id", "operator_action_idempotencies", ["actor_id"])
    op.create_index("ix_operator_action_idempotencies_resource_id", "operator_action_idempotencies", ["resource_id"])
    op.create_index("ix_operator_action_idempotencies_status", "operator_action_idempotencies", ["status"])
    op.create_index("ix_operator_action_idempotencies_result_resource_id", "operator_action_idempotencies", ["result_resource_id"])
    op.create_index("ix_operator_action_idempotencies_created_at", "operator_action_idempotencies", ["created_at"])
    op.create_index(
        "ix_operator_action_resource",
        "operator_action_idempotencies",
        ["tenant_id", "resource_type", "resource_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_operator_action_resource", table_name="operator_action_idempotencies")
    op.drop_index("ix_operator_action_idempotencies_created_at", table_name="operator_action_idempotencies")
    op.drop_index("ix_operator_action_idempotencies_result_resource_id", table_name="operator_action_idempotencies")
    op.drop_index("ix_operator_action_idempotencies_status", table_name="operator_action_idempotencies")
    op.drop_index("ix_operator_action_idempotencies_resource_id", table_name="operator_action_idempotencies")
    op.drop_index("ix_operator_action_idempotencies_actor_id", table_name="operator_action_idempotencies")
    op.drop_index("ix_operator_action_idempotencies_tenant_id", table_name="operator_action_idempotencies")
    op.drop_table("operator_action_idempotencies")
