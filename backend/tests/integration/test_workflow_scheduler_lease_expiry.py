"""Scheduler PostgreSQL 租约失效集成测试。

职责：验证旧 Scheduler owner 的 lease 过期后，新的 Scheduler 实例可以安全重新抢占。
边界：只验证真实 PostgreSQL Repository，不启动 API / Scheduler / Worker，也不执行 Workflow。
关键依赖：项目唯一数据库 Session、Workflow Scheduler Repository 与持久化模型。
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
    """数据库持久化测试必须由显式 Gate 开启，避免普通回归隐式依赖 PostgreSQL。"""
    if os.getenv("RUN_DATABASE_INTEGRATION") != "1":
        pytest.skip("需要设置 RUN_DATABASE_INTEGRATION=1 才执行 Scheduler PostgreSQL 租约测试")


@pytest_asyncio.fixture(autouse=True)
async def reset_database_engine_pool() -> None:
    """隔离 pytest-asyncio 事件循环，避免 asyncpg 连接跨测试循环复用。"""
    await engine.dispose()
    try:
        yield
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_scheduler_lease_can_be_reclaimed_by_new_owner() -> None:
    """验证 lease 过期后新 owner 可以抢占，而旧 owner 不能继续释放新 lease。"""
    tenant_id = uuid4()
    user_id = uuid4()
    workflow_id = uuid4()
    workflow_version_id = uuid4()
    trigger_id = uuid4()
    schedule_id = uuid4()
    now = utcnow_naive()

    async with SessionLocal() as setup_session:
        async with setup_session.begin():
            setup_session.add_all(
                [
                    Tenant(id=tenant_id, name=f"scheduler-expiry-{tenant_id}"),
                    User(
                        id=user_id,
                        username=f"scheduler-expiry-{user_id}",
                        password_hash="integration-test",
                        tenant_id=tenant_id,
                    ),
                    Workflow(
                        id=workflow_id,
                        name=f"scheduler-expiry-{workflow_id}",
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
                        name=f"scheduled-expiry-{trigger_id}",
                        trigger_type="scheduled",
                        status="enabled",
                        created_by=user_id,
                        config={},
                    ),
                ]
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
                    schedule_expression="interval:60",
                    next_run_at=now - timedelta(seconds=1),
                    lease_owner="scheduler-old",
                    lease_expires_at=now - timedelta(seconds=1),
                    misfire_policy="skip",
                    catch_up_limit=10,
                    updated_at=now,
                )
            )

    async with SessionLocal() as reclaim_session:
        repository = WorkflowSchedulerRepository(reclaim_session)
        reclaimed = await repository.claim_due_lease(
            schedule_id=schedule_id,
            tenant_id=tenant_id,
            owner="scheduler-new",
            now=now,
            lease_expires_at=now + timedelta(seconds=30),
        )
        assert reclaimed is not None
        assert reclaimed.lease_owner == "scheduler-new"
        assert reclaimed.lease_expires_at == now + timedelta(seconds=30)
        await reclaim_session.commit()

    async with SessionLocal() as stale_session:
        repository = WorkflowSchedulerRepository(stale_session)
        assert (
            await repository.release_lease(
                schedule_id=schedule_id,
                tenant_id=tenant_id,
                owner="scheduler-old",
                now=now,
            )
            is False
        )
        await stale_session.rollback()

    async with SessionLocal() as verify_session:
        persisted = await WorkflowSchedulerRepository(verify_session).get_schedule_for_trigger(
            tenant_id=tenant_id,
            trigger_id=trigger_id,
        )
        assert persisted is not None
        assert persisted.lease_owner == "scheduler-new"
        assert persisted.lease_expires_at == now + timedelta(seconds=30)
