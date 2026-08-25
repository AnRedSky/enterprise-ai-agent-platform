"""为 Workflow Execution 增加 Worker 租约字段。

职责：支持 Scheduler 创建 pending Execution 后，由独立 Worker Service 原子认领并执行。
边界：不改变 Execution 状态机语义；租约只用于 Worker ownership 与崩溃恢复。
"""
from alembic import op

revision = "0029_workflow_worker_lease"
down_revision = "0028_durable_scheduler_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """增加 Worker 租约字段与待执行索引。"""
    op.execute("ALTER TABLE workflow_executions ADD COLUMN worker_owner varchar(128) NULL")
    op.execute("ALTER TABLE workflow_executions ADD COLUMN worker_lease_expires_at timestamp NULL")
    op.execute("ALTER TABLE workflow_executions ADD COLUMN worker_attempt integer NOT NULL DEFAULT 0")
    op.execute("CREATE INDEX ix_workflow_execution_worker_claim ON workflow_executions (status, worker_lease_expires_at, created_at)")
    op.execute("""
        ALTER TABLE workflow_executions
        ADD CONSTRAINT ck_workflow_execution_worker_lease_pair
        CHECK ((worker_owner IS NULL AND worker_lease_expires_at IS NULL)
            OR (worker_owner IS NOT NULL AND worker_lease_expires_at IS NOT NULL))
    """)


def downgrade() -> None:
    """删除 Worker 租约字段与索引。"""
    op.execute("ALTER TABLE workflow_executions DROP CONSTRAINT IF EXISTS ck_workflow_execution_worker_lease_pair")
    op.execute("DROP INDEX IF EXISTS ix_workflow_execution_worker_claim")
    op.execute("ALTER TABLE workflow_executions DROP COLUMN IF EXISTS worker_attempt")
    op.execute("ALTER TABLE workflow_executions DROP COLUMN IF EXISTS worker_lease_expires_at")
    op.execute("ALTER TABLE workflow_executions DROP COLUMN IF EXISTS worker_owner")
