"""为 WorkflowNodeExecution 自动填充 tenant durable identity。

Revision ID: 0039_workflow_node_execution_tenant_trigger
Revises: 0038_agent_delegations
"""

from alembic import op
import sqlalchemy as sa

revision = "0039_workflow_node_execution_tenant_trigger"
down_revision = "0038_agent_delegations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION set_workflow_node_execution_tenant()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.tenant_id IS NULL THEN
                    SELECT tenant_id INTO NEW.tenant_id
                    FROM workflow_executions
                    WHERE id = NEW.execution_id;
                END IF;
                IF NEW.tenant_id IS NULL THEN
                    RAISE EXCEPTION 'workflow_node_executions execution_id has no tenant';
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_workflow_node_execution_tenant
            BEFORE INSERT ON workflow_node_executions
            FOR EACH ROW
            EXECUTE FUNCTION set_workflow_node_execution_tenant();
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_workflow_node_execution_tenant ON workflow_node_executions"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS set_workflow_node_execution_tenant()"))
