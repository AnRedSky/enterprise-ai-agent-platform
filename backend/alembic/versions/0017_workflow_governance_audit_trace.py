"""add workflow governance audit and trace

Revision ID: 0017_workflow_governance_audit_trace
Revises: 0016_workflow_execution_state_machine
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_workflow_governance_audit_trace"
down_revision = "0016_workflow_execution_state_machine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("tenant_id", sa.UUID(), nullable=True))
    op.add_column("audit_logs", sa.Column("workflow_id", sa.UUID(), nullable=True))
    op.add_column("audit_logs", sa.Column("workflow_version_id", sa.UUID(), nullable=True))
    op.add_column("audit_logs", sa.Column("workflow_execution_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_audit_logs_tenant", "audit_logs", "tenants", ["tenant_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_audit_logs_workflow", "audit_logs", "workflows", ["workflow_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_audit_logs_workflow_version", "audit_logs", "workflow_versions", ["workflow_version_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_audit_logs_workflow_execution", "audit_logs", "workflow_executions", ["workflow_execution_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"], unique=False)
    op.create_index("ix_audit_logs_workflow_id", "audit_logs", ["workflow_id"], unique=False)
    op.create_index("ix_audit_logs_workflow_execution_id", "audit_logs", ["workflow_execution_id"], unique=False)

    op.create_table(
        "workflow_trace_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("workflow_version_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.String(100), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["execution_id"], ["workflow_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workflow_version_id"], ["workflow_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
    )
    for name, column in (
        ("ix_workflow_trace_events_tenant_id", "tenant_id"),
        ("ix_workflow_trace_events_execution_id", "execution_id"),
        ("ix_workflow_trace_events_workflow_id", "workflow_id"),
        ("ix_workflow_trace_events_workflow_version_id", "workflow_version_id"),
        ("ix_workflow_trace_events_node_id", "node_id"),
        ("ix_workflow_trace_events_event_type", "event_type"),
        ("ix_workflow_trace_events_status", "status"),
        ("ix_workflow_trace_events_trace_id", "trace_id"),
        ("ix_workflow_trace_events_actor_id", "actor_id"),
    ):
        op.create_index(name, "workflow_trace_events", [column], unique=False)
    op.create_index("ix_workflow_trace_execution_created", "workflow_trace_events", ["execution_id", "created_at"], unique=False)
    op.create_index("ix_workflow_trace_tenant_created", "workflow_trace_events", ["tenant_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workflow_trace_tenant_created", table_name="workflow_trace_events")
    op.drop_index("ix_workflow_trace_execution_created", table_name="workflow_trace_events")
    for name in (
        "ix_workflow_trace_events_actor_id", "ix_workflow_trace_events_trace_id", "ix_workflow_trace_events_status",
        "ix_workflow_trace_events_event_type", "ix_workflow_trace_events_node_id", "ix_workflow_trace_events_workflow_version_id",
        "ix_workflow_trace_events_workflow_id", "ix_workflow_trace_events_execution_id", "ix_workflow_trace_events_tenant_id",
    ):
        op.drop_index(name, table_name="workflow_trace_events")
    op.drop_table("workflow_trace_events")
    op.drop_index("ix_audit_logs_workflow_execution_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_workflow_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_workflow_execution", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_workflow_version", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_workflow", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_tenant", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "workflow_execution_id")
    op.drop_column("audit_logs", "workflow_version_id")
    op.drop_column("audit_logs", "workflow_id")
    op.drop_column("audit_logs", "tenant_id")
