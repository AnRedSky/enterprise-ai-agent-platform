"""新增 Durable Scheduler 持久化模型与调度槽位幂等表

Revision ID: 0028_durable_scheduler_persistence
Revises: 0023_model_usage_accounting, 0027_retrieval_evaluation_vector_space
"""
from alembic import op

revision = "0028_durable_scheduler_persistence"
down_revision = ("0023_model_usage_accounting", "0027_retrieval_evaluation_vector_space")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE workflow_schedules (
            id uuid NOT NULL PRIMARY KEY,
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            trigger_id uuid NOT NULL REFERENCES workflow_triggers(id) ON DELETE CASCADE,
            workflow_id uuid NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            enabled boolean NOT NULL DEFAULT true,
            status varchar(20) NOT NULL DEFAULT 'enabled',
            timezone varchar(64) NOT NULL,
            schedule_expression varchar(255) NOT NULL,
            next_run_at timestamp NOT NULL,
            last_run_at timestamp NULL,
            last_execution_id uuid NULL REFERENCES workflow_executions(id) ON DELETE SET NULL,
            lease_owner varchar(128) NULL,
            lease_expires_at timestamp NULL,
            misfire_policy varchar(20) NOT NULL DEFAULT 'skip',
            catch_up_limit integer NOT NULL DEFAULT 10,
            updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_workflow_schedule_tenant_trigger UNIQUE (tenant_id, trigger_id),
            CONSTRAINT ck_workflow_schedule_status CHECK (status IN ('enabled', 'paused', 'disabled')),
            CONSTRAINT ck_workflow_schedule_enabled_state CHECK ((status = 'enabled' AND enabled = true) OR (status IN ('paused', 'disabled') AND enabled = false)),
            CONSTRAINT ck_workflow_schedule_misfire_policy CHECK (misfire_policy IN ('skip', 'fire_once', 'catch_up')),
            CONSTRAINT ck_workflow_schedule_catch_up_limit CHECK (catch_up_limit >= 1),
            CONSTRAINT ck_workflow_schedule_lease_pair CHECK ((lease_owner IS NULL AND lease_expires_at IS NULL) OR (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL))
        )
    """)
    op.execute("CREATE INDEX ix_workflow_schedule_due ON workflow_schedules (status, enabled, next_run_at)")
    op.execute("CREATE INDEX ix_workflow_schedule_tenant_status ON workflow_schedules (tenant_id, status)")
    op.execute("""
        CREATE TABLE workflow_schedule_slots (
            id uuid NOT NULL PRIMARY KEY,
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            trigger_id uuid NOT NULL REFERENCES workflow_triggers(id) ON DELETE CASCADE,
            workflow_id uuid NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            schedule_slot_key varchar(255) NOT NULL,
            planned_at timestamp NOT NULL,
            scheduler_owner varchar(128) NULL,
            workflow_execution_id uuid NULL REFERENCES workflow_executions(id) ON DELETE SET NULL,
            created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_workflow_schedule_slot_key UNIQUE (schedule_slot_key)
        )
    """)
    op.execute("CREATE INDEX ix_workflow_schedule_slot_trigger_planned ON workflow_schedule_slots (trigger_id, planned_at)")
    op.execute("CREATE INDEX ix_workflow_schedule_slot_tenant_created ON workflow_schedule_slots (tenant_id, created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_workflow_schedule_slot_tenant_created")
    op.execute("DROP INDEX IF EXISTS ix_workflow_schedule_slot_trigger_planned")
    op.execute("DROP TABLE IF EXISTS workflow_schedule_slots")
    op.execute("DROP INDEX IF EXISTS ix_workflow_schedule_tenant_status")
    op.execute("DROP INDEX IF EXISTS ix_workflow_schedule_due")
    op.execute("DROP TABLE IF EXISTS workflow_schedules")
