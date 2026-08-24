"""Scheduler Tenant Isolation 集成测试：验证状态查询不会跨租户读取调度记录。

职责：覆盖 WorkflowSchedulerRepository 的 tenant + trigger 查询边界。
边界：只验证真实 PostgreSQL Repository，不覆盖 API Contract、Runtime 或 Workflow Execution。
关键依赖：项目唯一数据库 Session、Scheduler Repository 与 Scheduler ORM 模型。
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio

from app.infrastructure.db import SessionLocal
from app.infrastructure.db.session import engine
from app.models.core import Tenant, User
from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_scheduler import WorkflowSchedule
from app.models.workflow_trigger import WorkflowTrigger
from app.services.workflow_scheduler.repository import WorkflowSchedulerRepository


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_database_integration() -> None:
    """数据库隔离测试必须由显式 Gate 开启。"""
    if os.getenv("RUN_DATABASE_INTEGRATION") != "1":
        pytest.skip("需要设置 RUN_DATABASE_INTEGRATION=1 才执行 Scheduler tenant isolation 测试")


@pytest_asyncio.fixture(autouse=True)
async def reset_database_engine_pool() -> None:
    """释放项目数据库连接池，避免真实 asyncpg 连接跨 pytest event loop 复用。"""
    await engine.dispose()
    try:
        yield
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_scheduler_status_lookup_is_tenant_scoped() -> None:
    """同一个 trigger ID 在错误 tenant 下必须读取不到 Scheduler 状态。"""
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    user_id = uuid4()
    workflow_id = uuid4()
    workflow_version_id = uuid4()
    trigger_id = uuid4()
    schedule_id = uuid4()

    async with SessionLocal() as session:
        async with session.begin():
            session.add_all(
                [
                    Tenant(id=tenant_id, name=f"scheduler-scope-{tenant_id}"),
                    Tenant(id=other_tenant_id, name=f"scheduler-scope-{other_tenant_id}"),
                    User(
                        id=user_id,
                        username=f"scheduler-scope-{user_id}",
                        password_hash="integration-test",
                        tenant_id=tenant_id,
                    ),
                    Workflow(
                        id=workflow_id,
                        name=f"scheduler-scope-{workflow_id}",
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
                ]
            )
            await session.flush()
            session.add(
                WorkflowTrigger(
                    id=trigger_id,
                    tenant_id=tenant_id,
                    workflow_id=workflow_id,
                    name=f"scheduler-scope-{trigger_id}",
                    trigger_type="scheduled",
                    status="enabled",
                    created_by=user_id,
                    config={"timezone": "UTC", "interval_seconds": 300},
                )
            )
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
                    schedule_expression="interval:300",
                    next_run_at=datetime.now(UTC).replace(tzinfo=None),
                    misfire_policy="skip",
                    catch_up_limit=10,
                )
            )

        repository = WorkflowSchedulerRepository(session)
        assert (await repository.get_schedule_for_trigger(tenant_id=tenant_id, trigger_id=trigger_id)) is not None
        assert (await repository.get_schedule_for_trigger(tenant_id=other_tenant_id, trigger_id=trigger_id)) is None
