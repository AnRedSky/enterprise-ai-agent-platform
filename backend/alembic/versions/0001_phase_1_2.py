"""phase 1.2 initial schema

Revision ID: 0001_phase_1_2
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_phase_1_2"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("users", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("username", sa.String(100), nullable=False, unique=True), sa.Column("password_hash", sa.Text(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("roles", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("name", sa.String(50), nullable=False, unique=True))
    op.create_table("user_roles", sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), sa.Column("role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("agents", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("name", sa.String(100), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("agent_versions", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False), sa.Column("version", sa.String(32), nullable=False), sa.Column("system_prompt", sa.Text(), nullable=False), sa.Column("model_id", sa.String(100), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("agent_id", "version", name="uq_agent_version"))
    op.create_table("sessions", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("messages", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("tools", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True), sa.Column("description", sa.Text(), nullable=False), sa.Column("endpoint", sa.String(500)), sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("agent_tools", sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True), sa.Column("tool_id", sa.Uuid(), sa.ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("audit_logs", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id")), sa.Column("action", sa.String(100), nullable=False), sa.Column("resource_type", sa.String(50), nullable=False), sa.Column("resource_id", sa.String(100)), sa.Column("request_id", sa.String(64)), sa.Column("trace_id", sa.String(64)), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.bulk_insert(sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String(50))), [{"id": "00000000-0000-0000-0000-000000000001", "name": "admin"}, {"id": "00000000-0000-0000-0000-000000000002", "name": "user"}])

def downgrade():
    for table in ["audit_logs", "agent_tools", "tools", "messages", "sessions", "agent_versions", "agents", "user_roles", "roles", "users"]:
        op.drop_table(table)
