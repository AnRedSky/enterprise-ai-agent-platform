"""确保 Workflow Execution 进入终态时原子释放 Worker ownership。

Revision ID: 0034
Revises: 0033_workflow_execution_resume_contract
"""

from alembic import op


revision = "0034_terminal_execution_releases_worker_lease"
down_revision = "0033_workflow_execution_resume_contract"
branch_labels = None
depends_on = None


_TRIGGER_FUNCTION = "workflow_execution_release_terminal_worker_lease"
_TRIGGER = "trg_workflow_execution_release_terminal_worker_lease"


def upgrade() -> None:
    """让 terminal status 与 Worker lease 释放处于同一数据库 UPDATE 原子边界。"""
    op.execute(
        f"""
        CREATE FUNCTION {_TRIGGER_FUNCTION}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.status IN ('completed', 'failed', 'cancelled') THEN
                NEW.worker_owner := NULL;
                NEW.worker_lease_expires_at := NULL;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {_TRIGGER}
        BEFORE UPDATE OF status ON workflow_executions
        FOR EACH ROW
        EXECUTE FUNCTION {_TRIGGER_FUNCTION}();
        """
    )


def downgrade() -> None:
    """删除终态 Worker lease 原子释放触发器。"""
    op.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER} ON workflow_executions")
    op.execute(f"DROP FUNCTION IF EXISTS {_TRIGGER_FUNCTION}()")
