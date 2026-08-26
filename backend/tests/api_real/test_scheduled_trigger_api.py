"""真实 HTTP Scheduler Trigger 验收：覆盖配置、幂等、多实例、misfire 恢复与治理关联。"""

import asyncio
import os
import time
import uuid
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
TRIGGER_WORKFLOW_ID = os.getenv("TRIGGER_WORKFLOW_ID")

pytestmark = pytest.mark.real_api


@pytest.fixture(scope="module")
def scheduler_event_loop():
    """创建只由本模块主动驱动的测试事件循环，避免 pytest-asyncio 生命周期接管并提前关闭。

    返回值：
        本模块复用的独立事件循环。
    """
    loop = asyncio.new_event_loop()
    try:
        # 不把专用循环注册为当前事件循环。pytest-asyncio 可能在测试阶段管理并关闭
        # 当前循环；本模块的异步操作全部显式通过 _run_async 驱动专用循环。
        yield loop
    finally:
        if not loop.is_closed():
            loop.close()


def _run_async(loop: asyncio.AbstractEventLoop, coroutine):
    """在测试专用事件循环中执行异步数据库操作。

    参数：
        loop: 当前模块复用的测试事件循环。
        coroutine: 待执行的协程对象。

    返回值：
        协程实际返回值。
    """
    return loop.run_until_complete(coroutine)


def _client() -> httpx.Client:
    """创建带真实 API Token 的 HTTP 客户端。

    返回值：
        指向当前 Real API 地址的 HTTP 客户端。
    """
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20.0,
    )


async def _execution_rows(idempotency_key: str) -> list[dict]:
    """读取指定 Scheduler slot 的真实 WorkflowExecution。

    参数：
        idempotency_key: Scheduler 统一生成的 slot 幂等键。

    返回值：
        按创建时间排序的真实 WorkflowExecution 行。
    """
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT id, status, idempotency_key, input_data "
                    "FROM workflow_executions "
                    "WHERE idempotency_key = :idempotency_key "
                    "ORDER BY created_at ASC"
                ),
                {"idempotency_key": idempotency_key},
            )
            return [dict(row._mapping) for row in result]
    finally:
        await engine.dispose()


async def _scheduled_execution_rows(trigger_id: str) -> list[dict]:
    """读取指定 Scheduled Trigger 已产生的真实 Execution，避免测试在 interval 边界计算陈旧 slot。

    参数：
        trigger_id: Scheduled Trigger 的 UUID 字符串。

    返回值：
        当前 Trigger 对应的全部 Scheduler Execution，按创建时间排序。
    """
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT id, status, idempotency_key, input_data "
                    "FROM workflow_executions "
                    "WHERE idempotency_key LIKE :prefix "
                    "ORDER BY created_at ASC"
                ),
                {"prefix": f"scheduled:{trigger_id}:%"},
            )
            return [dict(row._mapping) for row in result]
    finally:
        await engine.dispose()


async def _governance_rows(execution_id: str) -> tuple[list[dict], list[dict]]:
    """读取真实 PostgreSQL 中与 WorkflowExecution 绑定的 Audit/Trace 记录。

    参数：
        execution_id: WorkflowExecution 的 UUID 字符串。

    返回值：
        AuditLog 与 WorkflowTraceEvent 两组真实持久化记录。
    """
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            audit_result = await connection.execute(
                text(
                    "SELECT tenant_id, workflow_id, workflow_execution_id, action, status, metadata "
                    "FROM audit_logs WHERE workflow_execution_id = :execution_id ORDER BY created_at ASC"
                ),
                {"execution_id": uuid.UUID(execution_id)},
            )
            trace_result = await connection.execute(
                text(
                    "SELECT tenant_id, workflow_id, execution_id, event_type, status, data "
                    "FROM workflow_trace_events WHERE execution_id = :execution_id ORDER BY created_at ASC"
                ),
                {"execution_id": uuid.UUID(execution_id)},
            )
            return [dict(row._mapping) for row in audit_result], [dict(row._mapping) for row in trace_result]
    finally:
        await engine.dispose()


async def _seed_scheduler_backlog(trigger_id: str, next_run_at: datetime, interval_seconds: int) -> None:
    """直接把真实 Scheduler 持久化状态回拨一个槽位，模拟服务重启后存在历史积压的生产状态。

    参数：
        trigger_id: Scheduled Trigger 的 UUID 字符串。
        next_run_at: 要写入 Scheduler 的历史计划时间。
        interval_seconds: Scheduler interval 秒数，用于生成持久化表达式。

    返回值：
        无；函数直接更新 PostgreSQL 中的 Scheduler 状态。
    """
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            trigger = (
                await connection.execute(
                    text(
                        "SELECT tenant_id, workflow_id FROM workflow_triggers "
                        "WHERE id = :trigger_id"
                    ),
                    {"trigger_id": trigger_id},
                )
            ).mappings().one()
            await connection.execute(
                text(
                    "INSERT INTO workflow_schedules "
                    "(id, tenant_id, trigger_id, workflow_id, enabled, status, timezone, "
                    "schedule_expression, next_run_at, misfire_policy, catch_up_limit, updated_at) "
                    "VALUES (:id, :tenant_id, :trigger_id, :workflow_id, true, 'enabled', 'UTC', "
                    ":schedule_expression, :next_run_at, 'catch_up', 2, :updated_at)"
                ),
                {
                    "id": uuid.uuid4(),
                    "tenant_id": trigger["tenant_id"],
                    "trigger_id": uuid.UUID(trigger_id),
                    "workflow_id": trigger["workflow_id"],
                    "schedule_expression": f"interval:{interval_seconds}",
                    "next_run_at": next_run_at.replace(tzinfo=None),
                    "updated_at": datetime.now(UTC).replace(tzinfo=None),
                },
            )
    finally:
        await engine.dispose()


def _wait_for_scheduled_execution(
    loop: asyncio.AbstractEventLoop,
    idempotency_key: str,
    timeout_seconds: float = 15.0,
) -> list[dict]:
    """轮询真实 PostgreSQL，等待指定 slot 的 Execution 进入终态。

    参数：
        loop: 当前模块复用的测试事件循环。
        idempotency_key: 目标 Scheduler slot 的统一幂等键。
        timeout_seconds: 最大等待秒数。

    返回值：
        当前数据库中该幂等键对应的全部 Execution 行。
    """
    deadline = time.monotonic() + timeout_seconds
    terminal_states = {"completed", "failed", "cancelled"}
    while time.monotonic() < deadline:
        rows = _run_async(loop, _execution_rows(idempotency_key))
        if rows and all(row["status"] in terminal_states for row in rows):
            return rows
        time.sleep(1.0)
    return _run_async(loop, _execution_rows(idempotency_key))


def _wait_for_trigger_execution(
    loop: asyncio.AbstractEventLoop,
    trigger_id: str,
    timeout_seconds: float = 15.0,
) -> list[dict]:
    """轮询指定 Trigger 的真实 Execution，规避 interval 槽位边界导致的测试竞态。

    参数：
        loop: 当前模块复用的测试事件循环。
        trigger_id: Scheduled Trigger 的 UUID 字符串。
        timeout_seconds: 最大等待秒数。

    返回值：
        当前 Trigger 对应的已持久化 Execution 行。
    """
    deadline = time.monotonic() + timeout_seconds
    terminal_states = {"completed", "failed", "cancelled"}
    while time.monotonic() < deadline:
        rows = _run_async(loop, _scheduled_execution_rows(trigger_id))
        if rows and all(row["status"] in terminal_states for row in rows):
            return rows
        time.sleep(1.0)
    return _run_async(loop, _scheduled_execution_rows(trigger_id))


def test_scheduled_trigger_create_update_invoke_and_runtime_contract_real_http(scheduler_event_loop):
    """验证 Scheduled Trigger 的真实 HTTP 配置、禁止手工 invoke、真实 Execution 与治理关联。"""
    if not TRIGGER_WORKFLOW_ID:
        pytest.fail("TRIGGER_WORKFLOW_ID is required for scheduled Trigger validation")

    name = f"api-real-scheduled-{uuid.uuid4().hex[:8]}"
    config = {"timezone": "Asia/Shanghai", "interval_seconds": 60}
    updated_config = {"timezone": "UTC", "interval_seconds": 60}
    expected_config = {**config, "misfire_policy": "skip", "catch_up_limit": 10}
    expected_updated_config = {**updated_config, "misfire_policy": "skip", "catch_up_limit": 10}

    with _client() as client:
        created = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers",
            json={"name": name, "trigger_type": "scheduled", "config": config},
        )
        assert created.status_code == 201, created.text
        trigger = created.json()
        trigger_id = trigger["id"]
        assert trigger["trigger_type"] == "scheduled"
        assert trigger["status"] == "enabled"
        assert trigger["config"] == expected_config

        detail = client.get(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["config"] == expected_config

        updated = client.patch(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}",
            json={"config": updated_config},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["trigger_type"] == "scheduled"
        assert updated.json()["config"] == expected_updated_config

        invalid = client.patch(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}",
            json={"config": {"timezone": "Not/A_Timezone", "interval_seconds": 300}},
        )
        assert invalid.status_code == 422, invalid.text

        invoke = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}/invoke",
            json={"input_data": {"source": "scheduled-real-api"}},
        )
        assert invoke.status_code == 409, invoke.text
        assert "不可直接调用" in invoke.text

        rows = _wait_for_trigger_execution(scheduler_event_loop, trigger_id)
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "completed", rows
        runtime_key = rows[0]["idempotency_key"]
        assert runtime_key.startswith(f"scheduled:{trigger_id}:")
        runtime_slot = int(runtime_key.rsplit(":", 1)[1])
        assert rows[0]["input_data"]["scheduled_slot"] == runtime_slot
        assert rows[0]["input_data"]["recovery"] is False
        assert "planned_at" in rows[0]["input_data"]

        audit_rows, trace_rows = _run_async(scheduler_event_loop, _governance_rows(str(rows[0]["id"])))
        assert audit_rows, "Scheduled Execution 必须存在 tenant-scoped AuditLog"
        assert trace_rows, "Scheduled Execution 必须存在 tenant-scoped WorkflowTraceEvent"
        assert all(row["tenant_id"] is not None for row in audit_rows + trace_rows)
        assert all(row["workflow_id"] == uuid.UUID(TRIGGER_WORKFLOW_ID) for row in audit_rows + trace_rows)
        assert all(row["workflow_execution_id"] == rows[0]["id"] for row in audit_rows)
        assert all(row["execution_id"] == rows[0]["id"] for row in trace_rows)
        assert any(row["action"] == "workflow.trigger.scheduled" for row in audit_rows)
        assert any(row["event_type"] == "trigger.scheduled" for row in trace_rows)

        time.sleep(6)
        rows_after_duplicate_poll = _run_async(scheduler_event_loop, _execution_rows(runtime_key))
        assert len(rows_after_duplicate_poll) == 1, rows_after_duplicate_poll
        assert rows_after_duplicate_poll[0]["input_data"] == rows[0]["input_data"]

        disabled = client.patch(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}",
            json={"status": "disabled"},
        )
        assert disabled.status_code == 200, disabled.text

        deleted = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
        assert deleted.status_code == 204, deleted.text

        missing = client.get(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
        assert missing.status_code == 404, missing.text


def test_scheduled_trigger_two_workers_converge_on_one_slot_execution_real_http(scheduler_event_loop):
    """验证两个 Scheduler worker 对同一真实 PostgreSQL slot 只能收敛出一个 Execution。"""
    if not TRIGGER_WORKFLOW_ID:
        pytest.fail("TRIGGER_WORKFLOW_ID is required for multi-worker scheduler validation")

    name = f"api-real-scheduled-workers-{uuid.uuid4().hex[:8]}"
    config = {"timezone": "UTC", "interval_seconds": 60}
    trigger_id = None

    with _client() as client:
        created = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers",
            json={"name": name, "trigger_type": "scheduled", "config": config},
        )
        assert created.status_code == 201, created.text
        trigger_id = created.json()["id"]
        now = datetime(2020, 1, 1, 0, 0, 37, tzinfo=UTC)
        runtime_key = ScheduledTriggerScheduler.idempotency_key(trigger_id, now, config["interval_seconds"])

        async def dispatch_from_two_workers():
            """使用两个独立 Scheduler 实例竞争同一个持久化 slot。

            返回值：
                两个 worker 的 tick 计数结果。
            """
            first = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=1)
            second = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=1)
            return await asyncio.gather(first.tick_once(now), second.tick_once(now))

        try:
            counters = _run_async(scheduler_event_loop, dispatch_from_two_workers())
            rows = _wait_for_scheduled_execution(scheduler_event_loop, runtime_key)
            assert len(rows) == 1, rows
            assert rows[0]["idempotency_key"] == runtime_key
            assert rows[0]["input_data"]["scheduled_slot"] == ScheduledTriggerScheduler.interval_slot(
                now, config["interval_seconds"]
            )
            assert rows[0]["input_data"]["recovery"] is False
            assert sum(item["dispatched"] for item in counters) == 1
        finally:
            deleted = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
            assert deleted.status_code == 204, deleted.text


def test_scheduled_trigger_recovery_slot_persists_execution_metadata_real_http(scheduler_event_loop):
    """验证历史 misfire slot 与当前 slot 的真实 Execution 元数据及幂等恢复行为。"""
    if not TRIGGER_WORKFLOW_ID:
        pytest.fail("TRIGGER_WORKFLOW_ID is required for scheduled recovery validation")

    name = f"api-real-scheduled-recovery-{uuid.uuid4().hex[:8]}"
    config = {
        "timezone": "UTC",
        "interval_seconds": 60,
        "misfire_policy": "catch_up",
        "catch_up_limit": 2,
    }
    trigger_id = None

    with _client() as client:
        created = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers",
            json={"name": name, "trigger_type": "scheduled", "config": config},
        )
        assert created.status_code == 201, created.text
        trigger_id = created.json()["id"]

        now = datetime(2020, 1, 1, 0, 0, 37, tzinfo=UTC)
        scheduler = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=2)
        current_slot = scheduler.interval_slot(now, config["interval_seconds"])
        recovery_slot = current_slot - 1
        recovery_key = scheduler.slot_idempotency_key(trigger_id, recovery_slot)
        current_key = scheduler.slot_idempotency_key(trigger_id, current_slot)

        try:
            _run_async(
                scheduler_event_loop,
                _seed_scheduler_backlog(
                    trigger_id,
                    datetime.fromtimestamp(recovery_slot * config["interval_seconds"], UTC),
                    config["interval_seconds"],
                ),
            )
            counters = _run_async(scheduler_event_loop, scheduler.tick_once(now))
            recovery_rows = _wait_for_scheduled_execution(scheduler_event_loop, recovery_key)
            current_rows = _wait_for_scheduled_execution(scheduler_event_loop, current_key)

            assert counters["recovered"] >= 1, counters
            assert len(recovery_rows) == 1, recovery_rows
            assert len(current_rows) == 1, current_rows
            assert recovery_rows[0]["status"] == "completed", recovery_rows
            assert current_rows[0]["status"] == "completed", current_rows
            assert recovery_rows[0]["input_data"]["scheduled_slot"] == recovery_slot
            assert recovery_rows[0]["input_data"]["recovery"] is True
            assert current_rows[0]["input_data"]["scheduled_slot"] == current_slot
            assert current_rows[0]["input_data"]["recovery"] is False
            assert "planned_at" in recovery_rows[0]["input_data"]
            assert "planned_at" in current_rows[0]["input_data"]

            restarted = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=2)
            second_counters = _run_async(scheduler_event_loop, restarted.tick_once(now))
            assert second_counters["dispatched"] == 0, second_counters
            assert len(_run_async(scheduler_event_loop, _execution_rows(recovery_key))) == 1
            assert len(_run_async(scheduler_event_loop, _execution_rows(current_key))) == 1
        finally:
            deleted = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
            assert deleted.status_code == 204, deleted.text
