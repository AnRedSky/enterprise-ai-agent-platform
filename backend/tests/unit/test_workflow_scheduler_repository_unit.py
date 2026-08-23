"""Workflow Scheduler Repository 单元测试。

模块职责：验证 Scheduler Repository 的 SQL 构造与数据库冲突边界。
边界：只使用 AsyncMock/Mock，不访问真实 PostgreSQL；真实持久化验证位于 integration 层。
关键依赖：WorkflowSchedulerRepository 与 PostgreSQL SQL 编译器。
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.services.workflow_scheduler.repository import WorkflowSchedulerRepository


def _sql(statement) -> str:
    """使用 PostgreSQL 方言编译 SQL，避免单元测试建立真实数据库连接。"""
    return str(statement.compile(dialect=postgresql.dialect()))


async def test_claim_due_lease_is_single_atomic_update():
    db = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    repository = WorkflowSchedulerRepository(db)
    now = datetime(2026, 8, 23, 10, 0, tzinfo=timezone.utc)

    await repository.claim_due_lease(
        schedule_id=uuid4(), tenant_id=uuid4(), owner="worker-a", now=now,
        lease_expires_at=datetime(2026, 8, 23, 10, 1, tzinfo=timezone.utc),
    )

    statement = db.execute.await_args.args[0]
    sql = _sql(statement)
    assert sql.startswith("UPDATE workflow_schedules SET")
    assert "lease_owner" in sql
    assert "lease_expires_at" in sql
    assert "next_run_at" in sql
    assert "WHERE" in sql


async def test_release_lease_requires_current_owner():
    db = AsyncMock()
    result = Mock()
    result.rowcount = 1
    db.execute.return_value = result
    repository = WorkflowSchedulerRepository(db)

    released = await repository.release_lease(
        schedule_id=uuid4(), tenant_id=uuid4(), owner="worker-a",
        now=datetime(2026, 8, 23, 10, 0, tzinfo=timezone.utc),
    )

    assert released is True
    statement = db.execute.await_args.args[0]
    assert "lease_owner" in _sql(statement)


async def test_claim_schedule_slot_uses_database_unique_conflict_boundary():
    db = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    existing_result = Mock()
    existing_result.scalar_one_or_none.return_value = None
    db.execute.side_effect = [result, existing_result]
    repository = WorkflowSchedulerRepository(db)

    await repository.claim_schedule_slot(
        tenant_id=uuid4(), trigger_id=uuid4(), workflow_id=uuid4(),
        schedule_slot_key="trigger:2026-08-23T10:00:00+00:00",
        planned_at=datetime(2026, 8, 23, 10, 0, tzinfo=timezone.utc),
        scheduler_owner="worker-a",
    )

    statement = db.execute.await_args_list[0].args[0]
    sql = _sql(statement)
    assert "INSERT INTO workflow_schedule_slots" in sql
    assert "ON CONFLICT (schedule_slot_key) DO NOTHING" in sql
