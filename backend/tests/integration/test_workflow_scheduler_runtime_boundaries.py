"""Scheduler Runtime Due Candidate Discovery 边界集成测试。

职责：用真实 PostgreSQL 验证 Repository 原子候选查询只暴露当前真正到期的调度事实。
边界：不启动 API、Scheduler、Worker 或 Redis；所有测试身份与数据均由测试动态生成并在 finally 清理。
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.infrastructure.db import SessionLocal
from app.infrastructure.db.session import engine
from app.models.core import Tenant, User
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_scheduler import WorkflowSchedule
from app.models.workflow_trigger import WorkflowTrigger
from app.services.workflow_scheduler.repository import WorkflowSchedulerRepository
from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_database_integration() -> None:
    """数据库集成测试必须由显式 Gate 开启。"""
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


async def _cleanup(tenant_id, workflow_ids: list, version_ids: list, trigger_ids: list, schedule_ids: list) -> None:
    """删除本测试创建的全部持久化事实，保证共享数据库可重复验收。"""
    async with SessionLocal() as db:
        async with db.begin():
            await db.execute(text("DELETE FROM audit_logs WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM workflow_trace_events WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM integration_events WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM workflow_node_executions WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM workflow_frontiers WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM workflow_schedule_slots WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM workflow_executions WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            for schedule_id in schedule_ids:
                await db.execute(text("DELETE FROM workflow_schedules WHERE id = :id"), {"id": schedule_id})
            for trigger_id in trigger_ids:
                await db.execute(text("DELETE FROM workflow_triggers WHERE id = :id"), {"id": trigger_id})
            for workflow_id in workflow_ids:
                await db.execute(text("UPDATE workflows SET published_version_id = NULL WHERE id = :id"), {"id": workflow_id})
            for version_id in version_ids:
                await db.execute(text("DELETE FROM workflow_versions WHERE id = :id"), {"id": version_id})
            for workflow_id in workflow_ids:
                await db.execute(text("DELETE FROM workflows WHERE id = :id"), {"id": workflow_id})
            await db.execute(text("DELETE FROM users WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM tenants WHERE id = :tenant_id"), {"tenant_id": tenant_id})


async def _add_published_workflow(db, *, tenant_id, user_id, workflow_id, version_id, definition: dict) -> None:
    """创建一个已发布 Workflow，允许边界测试显式注入历史脏 Definition。"""
    # workflows.published_version_id 与 workflow_versions.workflow_id 构成相互依赖的外键。
    # 先以空 published_version_id 建立 Workflow，再写 Version，最后回填发布版本，才能满足数据库约束。
    db.add(
        Workflow(
            id=workflow_id,
            name=f"scheduler-boundary-{workflow_id}",
            owner_id=user_id,
            tenant_id=tenant_id,
            status="published",
            published_version_id=None,
        )
    )
    await db.flush()
    db.add(
        WorkflowVersion(
            id=version_id,
            workflow_id=workflow_id,
            version="1",
            definition=definition,
            status="published",
            created_by=user_id,
        )
    )
    await db.flush()
    await db.execute(
        text("UPDATE workflows SET published_version_id = :version_id WHERE id = :workflow_id"),
        {"version_id": version_id, "workflow_id": workflow_id},
    )


@pytest.mark.asyncio
async def test_scheduler_runtime_isolates_disabled_future_and_dirty_published_workflows() -> None:
    """验证全库存在脏 Definition 时，Runtime 只处理本测试租户真正到期的 enabled Schedule。"""
    tenant_id = uuid4()
    user_id = uuid4()
    target_workflow_id = uuid4()
    target_version_id = uuid4()
    target_trigger_id = uuid4()
    target_schedule_id = uuid4()
    disabled_workflow_id = uuid4()
    disabled_version_id = uuid4()
    disabled_trigger_id = uuid4()
    disabled_schedule_id = uuid4()
    future_workflow_id = uuid4()
    future_version_id = uuid4()
    future_trigger_id = uuid4()
    future_schedule_id = uuid4()
    missing_schedule_workflow_id = uuid4()
    missing_schedule_version_id = uuid4()
    missing_schedule_trigger_id = uuid4()
    now_aware = datetime.now(UTC)
    now = now_aware.replace(tzinfo=None)
    interval_seconds = 60
    workflow_ids = [target_workflow_id, disabled_workflow_id, future_workflow_id, missing_schedule_workflow_id]
    version_ids = [target_version_id, disabled_version_id, future_version_id, missing_schedule_version_id]
    trigger_ids = [target_trigger_id, disabled_trigger_id, future_trigger_id, missing_schedule_trigger_id]
    schedule_ids = [target_schedule_id, disabled_schedule_id, future_schedule_id]

    async with SessionLocal() as db:
        async with db.begin():
            db.add(Tenant(id=tenant_id, name=f"scheduler-boundary-{tenant_id}"))
            db.add(
                User(
                    id=user_id,
                    username=f"scheduler-boundary-{user_id}",
                    password_hash="integration-test",
                    tenant_id=tenant_id,
                )
            )
            await db.flush()

            await _add_published_workflow(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                workflow_id=target_workflow_id,
                version_id=target_version_id,
                definition={"nodes": [{"id": "input", "type": "input", "config": {}}]},
            )
            await _add_published_workflow(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                workflow_id=disabled_workflow_id,
                version_id=disabled_version_id,
                definition={},
            )
            await _add_published_workflow(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                workflow_id=future_workflow_id,
                version_id=future_version_id,
                definition={},
            )
            await _add_published_workflow(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                workflow_id=missing_schedule_workflow_id,
                version_id=missing_schedule_version_id,
                definition={},
            )

            for trigger_id, workflow_id, status in (
                (target_trigger_id, target_workflow_id, "enabled"),
                (disabled_trigger_id, disabled_workflow_id, "disabled"),
                (future_trigger_id, future_workflow_id, "enabled"),
                (missing_schedule_trigger_id, missing_schedule_workflow_id, "enabled"),
            ):
                db.add(
                    WorkflowTrigger(
                        id=trigger_id,
                        tenant_id=tenant_id,
                        workflow_id=workflow_id,
                        name=f"scheduler-boundary-{trigger_id}",
                        trigger_type="scheduled",
                        status=status,
                        created_by=user_id,
                        config={
                            "timezone": "UTC",
                            "interval_seconds": interval_seconds,
                            "misfire_policy": "skip",
                            "catch_up_limit": 10,
                        },
                    )
                )
            await db.flush()

            db.add_all(
                [
                    WorkflowSchedule(
                        id=target_schedule_id,
                        tenant_id=tenant_id,
                        trigger_id=target_trigger_id,
                        workflow_id=target_workflow_id,
                        enabled=True,
                        status="enabled",
                        timezone="UTC",
                        schedule_expression=f"interval:{interval_seconds}",
                        next_run_at=now - timedelta(seconds=interval_seconds),
                        misfire_policy="skip",
                        catch_up_limit=10,
                        updated_at=now,
                    ),
                    WorkflowSchedule(
                        id=disabled_schedule_id,
                        tenant_id=tenant_id,
                        trigger_id=disabled_trigger_id,
                        workflow_id=disabled_workflow_id,
                        enabled=False,
                        status="disabled",
                        timezone="UTC",
                        schedule_expression=f"interval:{interval_seconds}",
                        next_run_at=now - timedelta(seconds=interval_seconds),
                        misfire_policy="skip",
                        catch_up_limit=10,
                        updated_at=now,
                    ),
                    WorkflowSchedule(
                        id=future_schedule_id,
                        tenant_id=tenant_id,
                        trigger_id=future_trigger_id,
                        workflow_id=future_workflow_id,
                        enabled=True,
                        status="enabled",
                        timezone="UTC",
                        schedule_expression=f"interval:{interval_seconds}",
                        next_run_at=now + timedelta(seconds=interval_seconds * 10),
                        misfire_policy="skip",
                        catch_up_limit=10,
                        updated_at=now,
                    ),
                ]
            )

    try:
        async with SessionLocal() as db:
            candidates = await WorkflowSchedulerRepository(db).list_due_scheduled_candidates(now=now_aware)
            own_candidates = [
                (trigger.id, schedule.id)
                for trigger, _, schedule in candidates
                if trigger.tenant_id == tenant_id
            ]
            assert own_candidates == [(target_trigger_id, target_schedule_id)]

        scheduler = ScheduledTriggerScheduler(poll_interval_seconds=1, recovery_slots=2, lease_seconds=30)
        counters = await scheduler.tick_once(now_aware)
        # Scheduler Runtime 是多租户全库轮询，共享 PostgreSQL 可能同时存在其他租户的合法到期任务。
        assert counters["eligible"] >= 1, counters
        assert counters["dispatched"] >= 1, counters
        assert counters["failed"] == 0, counters

        async with SessionLocal() as db:
            dirty_executions = (
                await db.execute(
                    text(
                        "SELECT workflow_id FROM workflow_executions "
                        "WHERE tenant_id = :tenant_id ORDER BY created_at ASC"
                    ),
                    {"tenant_id": tenant_id},
                )
            ).scalars().all()
            assert dirty_executions == [target_workflow_id], dirty_executions

            schedules = (
                await db.execute(
                    text(
                        "SELECT id, next_run_at, enabled, status FROM workflow_schedules "
                        "WHERE tenant_id = :tenant_id ORDER BY id"
                    ),
                    {"tenant_id": tenant_id},
                )
            ).mappings().all()
            assert len(schedules) == 3, schedules
            future = next(row for row in schedules if row["id"] == future_schedule_id)
            disabled = next(row for row in schedules if row["id"] == disabled_schedule_id)
            assert future["next_run_at"] > now
            assert future["enabled"] is True and future["status"] == "enabled"
            assert disabled["enabled"] is False and disabled["status"] == "disabled"
    finally:
        await _cleanup(tenant_id, workflow_ids, version_ids, trigger_ids, schedule_ids)
