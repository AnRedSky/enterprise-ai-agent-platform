"""Scheduler Runtime PostgreSQL 闭环集成测试。

职责：验证 Scheduler Runtime 从持久化调度状态到 ScheduleSlot、WorkflowExecution、Durable Frontier、Audit/Trace 的真实事务闭环。
边界：不启动 API、Scheduler、Worker 或 Redis；只使用真实 PostgreSQL 和 Runtime 单次 tick。
关键依赖：SessionLocal、Scheduler Runtime、Scheduler 持久化模型与 Workflow Trigger Service。
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.infrastructure.db import SessionLocal
from app.infrastructure.db.session import engine
from app.models.core import Tenant, User
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_scheduler import WorkflowSchedule
from app.models.workflow_trigger import WorkflowTrigger
from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_database_integration() -> None:
    """数据库集成测试必须由显式 Gate 开启，避免普通回归隐式依赖 PostgreSQL。"""
    if os.getenv("RUN_DATABASE_INTEGRATION") != "1":
        pytest.skip("需要设置 RUN_DATABASE_INTEGRATION=1 才执行 Scheduler Runtime PostgreSQL 验收")


@pytest_asyncio.fixture(autouse=True)
async def reset_database_engine_pool() -> None:
    """隔离 pytest-asyncio 事件循环，避免 asyncpg 连接跨测试循环复用。"""
    await engine.dispose()
    try:
        yield
    finally:
        await engine.dispose()


async def _cleanup(tenant_id, workflow_id, workflow_version_id, trigger_id, schedule_id) -> None:
    """删除本测试创建的持久化事实，并等待后台 Runtime 释放本测试版本的引用。

    共享 PostgreSQL 中可能存在独立 Worker 继续消费本测试刚创建的 Durable Frontier。
    仅依赖固定删除顺序或 deadlock 重试仍存在竞态：Worker 可以在删除 Execution 后重新提交
    对 WorkflowVersion 的引用，随后使删除 WorkflowVersion 触发外键冲突。清理事务首先对
    WorkflowVersion 加排他行锁；PostgreSQL 外键检查需要的 KEY SHARE 锁与该锁冲突，因此
    后续 Worker 无法在清理事务内重新建立引用。事务再按子表到父表顺序删除，保证清理闭环。
    """
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            async with SessionLocal() as db:
                async with db.begin():
                    await db.execute(
                        text(
                            "SELECT id FROM workflow_versions "
                            "WHERE id = :workflow_version_id FOR UPDATE"
                        ),
                        {"workflow_version_id": workflow_version_id},
                    )
                    await db.execute(text("DELETE FROM audit_logs WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await db.execute(text("DELETE FROM workflow_trace_events WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await db.execute(text("DELETE FROM integration_events WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await db.execute(text("DELETE FROM workflow_node_executions WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await db.execute(text("DELETE FROM workflow_frontiers WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await db.execute(text("DELETE FROM workflow_schedule_slots WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await db.execute(text("DELETE FROM workflow_executions WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await db.execute(text("DELETE FROM workflow_schedules WHERE id = :schedule_id"), {"schedule_id": schedule_id})
                    await db.execute(text("DELETE FROM workflow_triggers WHERE id = :trigger_id"), {"trigger_id": trigger_id})
                    await db.execute(text("UPDATE workflows SET published_version_id = NULL WHERE id = :workflow_id"), {"workflow_id": workflow_id})
                    await db.execute(text("DELETE FROM workflow_versions WHERE id = :workflow_version_id"), {"workflow_version_id": workflow_version_id})
                    await db.execute(text("DELETE FROM workflows WHERE id = :workflow_id"), {"workflow_id": workflow_id})
                    await db.execute(text("DELETE FROM users WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await db.execute(text("DELETE FROM tenants WHERE id = :tenant_id"), {"tenant_id": tenant_id})
            return
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) != "40P01" or attempt == max_attempts - 1:
                raise
            await asyncio.sleep(0.1 * (attempt + 1))


@pytest.mark.asyncio
async def test_scheduler_runtime_persists_misfire_execution_and_governance_chain() -> None:
    """验证 catch_up 两个历史槽位形成唯一 Slot/Execution/Frontier，并完整落下 Audit/Trace。"""
    tenant_id = uuid4()
    user_id = uuid4()
    workflow_id = uuid4()
    workflow_version_id = uuid4()
    trigger_id = uuid4()
    schedule_id = uuid4()
    now_aware = datetime.now(UTC)
    now = now_aware.replace(tzinfo=None)
    interval_seconds = 60

    async with SessionLocal() as setup_session:
        async with setup_session.begin():
            setup_session.add(Tenant(id=tenant_id, name=f"scheduler-runtime-{tenant_id}"))
            setup_session.add(User(id=user_id, username=f"scheduler-runtime-{user_id}", password_hash="integration-test", tenant_id=tenant_id))
            setup_session.add(Workflow(id=workflow_id, name=f"scheduler-runtime-{workflow_id}", owner_id=user_id, tenant_id=tenant_id, status="published"))
            setup_session.add(
                WorkflowVersion(
                    id=workflow_version_id,
                    workflow_id=workflow_id,
                    version="1",
                    definition={"nodes": [{"id": "scheduled-input", "type": "input", "config": {}}]},
                    status="published",
                    created_by=user_id,
                )
            )
            await setup_session.flush()
            await setup_session.execute(text("UPDATE workflows SET published_version_id = :version_id WHERE id = :workflow_id"), {"version_id": workflow_version_id, "workflow_id": workflow_id})
            setup_session.add(
                WorkflowTrigger(
                    id=trigger_id,
                    tenant_id=tenant_id,
                    workflow_id=workflow_id,
                    name=f"scheduled-runtime-{trigger_id}",
                    trigger_type="scheduled",
                    status="enabled",
                    created_by=user_id,
                    config={"timezone": "UTC", "interval_seconds": interval_seconds, "misfire_policy": "catch_up", "catch_up_limit": 2},
                )
            )
            await setup_session.flush()
            setup_session.add(
                WorkflowSchedule(
                    id=schedule_id,
                    tenant_id=tenant_id,
                    trigger_id=trigger_id,
                    workflow_id=workflow_id,
                    enabled=True,
                    status="enabled",
                    timezone="UTC",
                    schedule_expression=f"interval:{interval_seconds}",
                    next_run_at=now - timedelta(seconds=interval_seconds),
                    misfire_policy="catch_up",
                    catch_up_limit=2,
                    updated_at=now,
                )
            )

    scheduler = ScheduledTriggerScheduler(poll_interval_seconds=1, recovery_slots=2, lease_seconds=30)
    try:
        counters = await scheduler.tick_once(now_aware)
        assert counters["eligible"] >= 1, counters
        assert counters["dispatched"] >= 2, counters
        assert counters["recovered"] >= 1, counters
        assert counters["failed"] == 0, counters

        async with SessionLocal() as verify_session:
            schedule = (await verify_session.execute(text("SELECT next_run_at, last_run_at, last_execution_id, lease_owner, lease_expires_at FROM workflow_schedules WHERE id = :schedule_id"), {"schedule_id": schedule_id})).mappings().one()
            assert schedule["next_run_at"] > now
            assert schedule["last_run_at"] == now
            assert schedule["lease_owner"] is None
            assert schedule["lease_expires_at"] is None

            slots = (await verify_session.execute(text("SELECT id, schedule_slot_key, planned_at, workflow_execution_id FROM workflow_schedule_slots WHERE tenant_id = :tenant_id ORDER BY planned_at ASC"), {"tenant_id": tenant_id})).mappings().all()
            assert len(slots) == 2, slots
            assert all(row["workflow_execution_id"] is not None for row in slots)
            assert slots[0]["planned_at"] < slots[1]["planned_at"]

            executions = (await verify_session.execute(text("SELECT id, status, idempotency_key, input_data FROM workflow_executions WHERE tenant_id = :tenant_id ORDER BY created_at ASC"), {"tenant_id": tenant_id})).mappings().all()
            assert len(executions) == 2, executions
            assert {row["id"] for row in executions} == {row["workflow_execution_id"] for row in slots}
            assert all(row["status"] in {"pending", "running", "completed"} for row in executions), executions
            assert all(row["idempotency_key"].startswith(f"scheduled:{trigger_id}:") for row in executions)
            assert any(row["input_data"]["recovery"] is True for row in executions)
            assert any(row["input_data"]["recovery"] is False for row in executions)

            frontiers = (await verify_session.execute(text("SELECT execution_id, status FROM workflow_frontiers WHERE tenant_id = :tenant_id ORDER BY created_at ASC"), {"tenant_id": tenant_id})).mappings().all()
            assert len(frontiers) == 2, frontiers
            assert {row["execution_id"] for row in frontiers} == {row["id"] for row in executions}
            assert all(row["status"] in {"pending", "retry_wait", "claimed", "running", "completed"} for row in frontiers), frontiers

            audits = (await verify_session.execute(text("SELECT workflow_execution_id, action, status FROM audit_logs WHERE tenant_id = :tenant_id ORDER BY created_at ASC"), {"tenant_id": tenant_id})).mappings().all()
            traces = (await verify_session.execute(text("SELECT execution_id, event_type, status FROM workflow_trace_events WHERE tenant_id = :tenant_id ORDER BY created_at ASC"), {"tenant_id": tenant_id})).mappings().all()
            assert len([row for row in audits if row["action"] == "workflow.trigger.scheduled"]) == 1, audits
            assert len([row for row in audits if row["action"] == "workflow.trigger.scheduled_recovery"]) == 1, audits
            assert len([row for row in traces if row["event_type"] == "trigger.scheduled"]) == 1, traces
            assert len([row for row in traces if row["event_type"] == "trigger.scheduled.recovery"]) == 1, traces
            assert {row["workflow_execution_id"] for row in audits} <= {row["id"] for row in executions}
            assert {row["execution_id"] for row in traces} <= {row["id"] for row in executions}
    finally:
        await _cleanup(tenant_id, workflow_id, workflow_version_id, trigger_id, schedule_id)
