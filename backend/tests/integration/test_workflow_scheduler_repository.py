"""Scheduler PostgreSQL 集成测试：验证持久化租约、槽位幂等与租户隔离。

边界：只验证真实 PostgreSQL Repository 行为，不模拟业务数据库，也不覆盖 API / Runtime。
关键依赖：项目唯一数据库 Session、Scheduler Repository 与 Workflow Scheduler 持久化模型。
"""

from __future__ import annotations

import os
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio

from app.infrastructure.db import SessionLocal
from app.infrastructure.db.session import engine
from app.models.core import Tenant, User, utcnow_naive
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_scheduler import WorkflowSchedule
from app.models.workflow_trigger import WorkflowTrigger
from app.services.workflow_scheduler.repository import WorkflowSchedulerRepository


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_database_integration() -> None:
    """数据库持久化测试必须由显式 Gate 开启，避免普通单元回归隐式依赖 PostgreSQL。"""
    if os.getenv("RUN_DATABASE_INTEGRATION") != "1":
        pytest.skip("需要设置 RUN_DATABASE_INTEGRATION=1 才执行 Scheduler PostgreSQL 持久化测试")


@pytest_asyncio.fixture(autouse=True)
async def reset_database_engine_pool() -> None:
    """隔离 pytest-asyncio 测试事件循环，避免 asyncpg 连接跨测试循环复用。

    该测试文件使用项目唯一数据库 Engine。pytest-asyncio 的函数级事件循环会在每个测试结束后关闭，
    而 SQLAlchemy 默认连接池可能保留绑定旧事件循环的 asyncpg 连接；在测试前后释放连接池可保持真实
    PostgreSQL 测试语义，同时避免 Windows Proactor 下出现 `Event loop is closed`。
    """
    await engine.dispose()
    try:
        yield
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_scheduler_repository_claim_release_and_tenant_isolation() -> None:
    """验证租约原子抢占、owner 释放以及 tenant 隔离边界。"""
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    user_id = uuid4()
    workflow_id = uuid4()
    workflow_version_id = uuid4()
    trigger_id = uuid4()
    schedule_id = uuid4()
    now = utcnow_naive()

    async with SessionLocal() as session:
        async with session.begin():
            session.add_all(
                [
                    Tenant(id=tenant_id, name=f"scheduler-{tenant_id}"),
                    Tenant(id=other_tenant_id, name=f"scheduler-{other_tenant_id}"),
                    User(
                        id=user_id,
                        username=f"scheduler-{user_id}",
                        password_hash="integration-test",
                        tenant_id=tenant_id,
                    ),
                    Workflow(
                        id=workflow_id,
                        name=f"scheduler-{workflow_id}",
                        owner_id=user_id,
                        tenant_id=tenant_id,
                        status="published",
                    ),
                    WorkflowVersion(
                        id=workflow_version_id,
                        workflow_id=workflow_id,
                        version="1",
                        definition={},
                        status="published",
                        created_by=user_id,
                    ),
                    WorkflowTrigger(
                        id=trigger_id,
                        tenant_id=tenant_id,
                        workflow_id=workflow_id,
                        name=f"scheduled-{trigger_id}",
                        trigger_type="scheduled",
                        status="enabled",
                        created_by=user_id,
                        config={},
                    ),
                ]
            )
            # 先提交 FK 前置实体，再建立依赖 Trigger 的 Schedule，避免无 ORM relationship 时 flush 顺序不稳定。
            await session.flush()
            session.add(
                WorkflowSchedule(
                    id=schedule_id,
                    tenant_id=tenant_id,
                    trigger_id=trigger_id,
                    workflow_id=workflow_id,
                    enabled=True,
                    status="enabled",
                    timezone="UTC",
                    schedule_expression="*/5 * * * *",
                    next_run_at=now - timedelta(minutes=1),
                    misfire_policy="skip",
                    catch_up_limit=10,
                    updated_at=now,
                )
            )

        repository = WorkflowSchedulerRepository(session)
        claimed = await repository.claim_due_lease(
            schedule_id=schedule_id,
            tenant_id=tenant_id,
            owner="worker-a",
            now=now,
            lease_expires_at=now + timedelta(minutes=1),
        )
        assert claimed is not None
        assert claimed.lease_owner == "worker-a"
        await session.commit()

        async with SessionLocal() as second_session:
            second_repository = WorkflowSchedulerRepository(second_session)
            assert (
                await second_repository.claim_due_lease(
                    schedule_id=schedule_id,
                    tenant_id=tenant_id,
                    owner="worker-b",
                    now=now,
                    lease_expires_at=now + timedelta(minutes=1),
                )
                is None
            )
            assert (
                await second_repository.claim_due_lease(
                    schedule_id=schedule_id,
                    tenant_id=other_tenant_id,
                    owner="worker-b",
                    now=now,
                    lease_expires_at=now + timedelta(minutes=1),
                )
                is None
            )

        assert await repository.release_lease(
            schedule_id=schedule_id,
            tenant_id=tenant_id,
            owner="worker-b",
            now=now,
        ) is False
        assert await repository.release_lease(
            schedule_id=schedule_id,
            tenant_id=tenant_id,
            owner="worker-a",
            now=now,
        ) is True
        await session.rollback()


@pytest.mark.asyncio
async def test_scheduler_repository_slot_claim_is_idempotent() -> None:
    """验证 schedule_slot_key 唯一键在重复 claim 时返回同一槽位。"""
    tenant_id = uuid4()
    user_id = uuid4()
    workflow_id = uuid4()
    workflow_version_id = uuid4()
    trigger_id = uuid4()
    now = utcnow_naive()
    slot_key = f"scheduler-test-{uuid4()}"

    async with SessionLocal() as session:
        async with session.begin():
            session.add_all(
                [
                    Tenant(id=tenant_id, name=f"slot-{tenant_id}"),
                    User(
                        id=user_id,
                        username=f"slot-{user_id}",
                        password_hash="integration-test",
                        tenant_id=tenant_id,
                    ),
                    Workflow(
                        id=workflow_id,
                        name=f"slot-{workflow_id}",
                        owner_id=user_id,
                        tenant_id=tenant_id,
                    ),
                    WorkflowVersion(
                        id=workflow_version_id,
                        workflow_id=workflow_id,
                        version="1",
                        definition={},
                        created_by=user_id,
                    ),
                    WorkflowTrigger(
                        id=trigger_id,
                        tenant_id=tenant_id,
                        workflow_id=workflow_id,
                        name=f"slot-trigger-{trigger_id}",
                        trigger_type="scheduled",
                        created_by=user_id,
                    ),
                ]
            )
            await session.flush()

        repository = WorkflowSchedulerRepository(session)
        first = await repository.claim_schedule_slot(
            tenant_id=tenant_id,
            trigger_id=trigger_id,
            workflow_id=workflow_id,
            schedule_slot_key=slot_key,
            planned_at=now,
            scheduler_owner="worker-a",
        )
        assert first is not None
        await session.commit()

        async with SessionLocal() as second_session:
            second_repository = WorkflowSchedulerRepository(second_session)
            second = await second_repository.claim_schedule_slot(
                tenant_id=tenant_id,
                trigger_id=trigger_id,
                workflow_id=workflow_id,
                schedule_slot_key=slot_key,
                planned_at=now,
                scheduler_owner="worker-b",
            )
            assert second is not None
            assert second.id == first.id

        await session.rollback()
