from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.services.workflow_scheduler.repository import WorkflowSchedulerRepository


async def test_claim_due_lease_uses_single_atomic_update():
    db = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    repository = WorkflowSchedulerRepository(db)

    await repository.claim_due_lease(
        schedule_id=uuid4(),
        tenant_id=uuid4(),
        owner="worker-a",
        now=datetime(2026, 8, 23, 10, 0),
        lease_expires_at=datetime(2026, 8, 23, 10, 1),
    )

    assert db.execute.await_count == 1
    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert sql.startswith("UPDATE workflow_schedules SET")


async def test_claim_schedule_slot_uses_database_unique_conflict_boundary():
    db = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    existing_result = Mock()
    existing_result.scalar_one_or_none.return_value = None
    db.execute.side_effect = [result, existing_result]
    repository = WorkflowSchedulerRepository(db)

    await repository.claim_schedule_slot(
        tenant_id=uuid4(),
        trigger_id=uuid4(),
        workflow_id=uuid4(),
        schedule_slot_key="trigger:2026-08-23T10:00:00+00:00",
        planned_at=datetime(2026, 8, 23, 10, 0, tzinfo=timezone.utc),
        scheduler_owner="worker-a",
    )

    statement = db.execute.await_args_list[0].args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (schedule_slot_key) DO NOTHING" in sql


async def test_claim_due_lease_normalizes_timezone_aware_datetimes_for_postgres():
    db = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    repository = WorkflowSchedulerRepository(db)

    now = datetime(2026, 8, 23, 10, 0, tzinfo=timezone.utc)
    lease_expires_at = datetime(2026, 8, 23, 10, 1, tzinfo=timezone.utc)
    await repository.claim_due_lease(
        schedule_id=uuid4(),
        tenant_id=uuid4(),
        owner="worker-a",
        now=now,
        lease_expires_at=lease_expires_at,
    )

    statement = db.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    params = compiled.params
    datetime_params = [value for value in params.values() if isinstance(value, datetime)]
    assert datetime_params
    assert datetime(2026, 8, 23, 10, 0) in datetime_params
    assert datetime(2026, 8, 23, 10, 1) in datetime_params
    assert all(value.tzinfo is None for value in datetime_params)


async def test_claim_schedule_slot_normalizes_timezone_aware_planned_at():
    db = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    existing_result = Mock()
    existing_result.scalar_one_or_none.return_value = None
    db.execute.side_effect = [result, existing_result]
    repository = WorkflowSchedulerRepository(db)

    await repository.claim_schedule_slot(
        tenant_id=uuid4(),
        trigger_id=uuid4(),
        workflow_id=uuid4(),
        schedule_slot_key="trigger:2026-08-23T10:00:00+00:00",
        planned_at=datetime(2026, 8, 23, 10, 0, tzinfo=timezone.utc),
        scheduler_owner="worker-a",
    )

    statement = db.execute.await_args_list[0].args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert all(value.tzinfo is None for value in compiled.params.values() if isinstance(value, datetime))
