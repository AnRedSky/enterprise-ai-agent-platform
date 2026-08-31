"""移除历史 audit_logs.execution_id 的失效外键约束。

Revision ID: 0013_remove_legacy_audit_execution_fk
Revises: 0012_execution_event_metadata

历史可观测性模型曾把 audit_logs.execution_id 指向已废弃的 executions 表。
当前 Workflow Execution 正式关联字段为 workflow_execution_id；execution_id 仅用于读取历史审计数据，
因此必须保持为普通 UUID 列，不能继续通过外键约束阻断历史数据写入。
"""

from alembic import op

revision = "0013_remove_legacy_audit_execution_fk"
down_revision = "0012_execution_event_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """移除可能残留的历史 executions 外键；新数据库没有该约束时安全跳过。"""
    op.execute(
        "ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS fk_audit_execution"
    )


def downgrade() -> None:
    """恢复历史外键仅用于向下迁移；存在孤立历史值时 PostgreSQL 会拒绝恢复。"""
    op.create_foreign_key(
        "fk_audit_execution",
        "audit_logs",
        "executions",
        ["execution_id"],
        ["id"],
    )
