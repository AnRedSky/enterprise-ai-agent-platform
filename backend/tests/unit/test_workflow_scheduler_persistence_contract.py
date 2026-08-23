from sqlalchemy import inspect

from app.models.workflow_scheduler import WorkflowSchedule, WorkflowScheduleSlot


def test_workflow_schedule_persistence_contract_exposes_required_fields():
    columns = {column.name for column in inspect(WorkflowSchedule).columns}
    assert columns >= {"tenant_id", "trigger_id", "workflow_id", "enabled", "status", "timezone", "schedule_expression", "next_run_at", "last_run_at", "last_execution_id", "lease_owner", "lease_expires_at", "misfire_policy", "catch_up_limit", "updated_at"}


def test_workflow_schedule_slot_persistence_contract_has_durable_idempotency_key():
    columns = {column.name for column in inspect(WorkflowScheduleSlot).columns}
    assert columns >= {"tenant_id", "trigger_id", "workflow_id", "schedule_slot_key", "planned_at", "scheduler_owner", "workflow_execution_id", "created_at"}
    constraints = {constraint.name for constraint in WorkflowScheduleSlot.__table__.constraints}
    assert "uq_workflow_schedule_slot_key" in constraints
