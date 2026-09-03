"""真实 HTTP Scheduler Trigger 验收：自动生成隔离测试上下文并覆盖调度闭环。"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
TRIGGER_WORKFLOW_ID = os.getenv("TRIGGER_WORKFLOW_ID")
_AUTO_TENANT_ID: str | None = None
_AUTO_USER_ID: str | None = None
_AUTO_WORKFLOW_ID: str | None = None
_AUTO_VERSION_ID: str | None = None

pytestmark = pytest.mark.real_api


@pytest.fixture(scope="module")
def scheduler_event_loop():
    """创建本模块独立事件循环，避免数据库连接跨测试循环复用。"""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        if not loop.is_closed():
            loop.close()


def _run_async(loop: asyncio.AbstractEventLoop, coroutine):
    """在测试专用事件循环执行异步操作。"""
    return loop.run_until_complete(coroutine)


def _client() -> httpx.Client:
    """创建当前 Real API 的认证客户端。"""
    if not TOKEN:
        pytest.fail("Real API test context bootstrap failed: ACCESS_TOKEN is unavailable")
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=20.0)


def _test_engine():
    """创建不跨事件循环复用连接的测试数据库引擎。"""
    return create_async_engine(settings.database_url, poolclass=NullPool, pool_pre_ping=True)


def _test_session_factory():
    """创建仅供本模块 Scheduler Runtime 使用的独立 Session 工厂。"""
    engine = _test_engine()
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def _request(client: httpx.Client, method: str, path: str, **kwargs) -> httpx.Response:
    """执行 Real API 请求并在失败时提供完整响应。"""
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise AssertionError(f"{method} {path} -> {response.status_code}: {response.text}")
    return response


async def _cleanup_auto_context(tenant_id: str, workflow_id: str) -> None:
    """按外键依赖顺序清理自动生成 Tenant 的全部运行时事实。"""
    engine = _test_engine()
    try:
        async with engine.begin() as connection:
            statements = [
                "DELETE FROM audit_logs WHERE tenant_id = :tenant_id",
                "DELETE FROM workflow_trace_events WHERE tenant_id = :tenant_id",
                "DELETE FROM integration_events WHERE tenant_id = :tenant_id",
                "DELETE FROM workflow_node_executions WHERE tenant_id = :tenant_id",
                "DELETE FROM workflow_frontiers WHERE tenant_id = :tenant_id",
                "DELETE FROM workflow_schedule_slots WHERE tenant_id = :tenant_id",
                "DELETE FROM workflow_executions WHERE tenant_id = :tenant_id",
                "DELETE FROM workflow_schedules WHERE tenant_id = :tenant_id",
                "DELETE FROM workflow_triggers WHERE tenant_id = :tenant_id",
                "UPDATE workflows SET published_version_id = NULL WHERE id = :workflow_id",
                "DELETE FROM workflow_versions WHERE workflow_id = :workflow_id",
                "DELETE FROM workflows WHERE tenant_id = :tenant_id",
                "DELETE FROM organization_memberships WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :tenant_id)",
                "DELETE FROM organizations WHERE tenant_id = :tenant_id",
                "DELETE FROM users WHERE tenant_id = :tenant_id",
                "DELETE FROM tenants WHERE id = :tenant_id",
            ]
            params = {"tenant_id": uuid.UUID(tenant_id), "workflow_id": uuid.UUID(workflow_id)}
            for statement in statements:
                await connection.execute(text(statement), params)
    finally:
        await engine.dispose()


@pytest.fixture(scope="module", autouse=True)
def scheduled_trigger_real_api_context(scheduler_event_loop):
    """自动生成隔离 Tenant/User/Workflow/Version；Gate 已提供 context 时直接复用。"""
    global TOKEN, TRIGGER_WORKFLOW_ID
    global _AUTO_TENANT_ID, _AUTO_USER_ID, _AUTO_WORKFLOW_ID, _AUTO_VERSION_ID

    if TOKEN and TRIGGER_WORKFLOW_ID:
        yield
        return

    username = f"api_real_scheduler_{uuid.uuid4().hex[:12]}"
    password = f"ApiRealTest!{uuid.uuid4().hex[:20]}"
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        registered = _request(client, "POST", "/auth/register", json={"username": username, "password": password}).json()
        login = _request(client, "POST", "/auth/login", json={"username": username, "password": password}).json()
        TOKEN = str(login["access_token"])
        _AUTO_TENANT_ID = str(login["tenant_id"])
        _AUTO_USER_ID = str(login["user_id"])
        client.headers["Authorization"] = f"Bearer {TOKEN}"
        workflow = _request(
            client,
            "POST",
            "/workflows",
            json={"name": f"API Real Scheduler {uuid.uuid4().hex[:8]}", "description": "自动生成 Scheduler Real API 验收 Workflow"},
        ).json()
        _AUTO_WORKFLOW_ID = str(workflow["id"])
        TRIGGER_WORKFLOW_ID = _AUTO_WORKFLOW_ID
        version = _request(
            client,
            "POST",
            f"/workflows/{_AUTO_WORKFLOW_ID}/versions",
            json={
                "definition": {
                    "nodes": [
                        {"id": "scheduled-input", "type": "input", "config": {}},
                        {"id": "scheduled-output", "type": "output", "config": {}},
                    ],
                    "edges": [{"source": "scheduled-input", "target": "scheduled-output"}],
                }
            },
        ).json()
        _AUTO_VERSION_ID = str(version["id"])
        _request(client, "POST", f"/workflows/{_AUTO_WORKFLOW_ID}/versions/{_AUTO_VERSION_ID}/publish")

    yield

    if _AUTO_TENANT_ID and _AUTO_WORKFLOW_ID:
        _run_async(scheduler_event_loop, _cleanup_auto_context(_AUTO_TENANT_ID, _AUTO_WORKFLOW_ID))
    TOKEN = None
    TRIGGER_WORKFLOW_ID = None


async def _execution_rows(idempotency_key: str) -> list[dict]:
    """读取指定 Scheduler slot 的真实 WorkflowExecution。"""
    engine = _test_engine()
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT id, status, idempotency_key, input_data FROM workflow_executions WHERE idempotency_key = :idempotency_key ORDER BY created_at ASC"),
                {"idempotency_key": idempotency_key},
            )
            return [dict(row._mapping) for row in result]
    finally:
        await engine.dispose()


async def _scheduled_execution_rows(trigger_id: str) -> list[dict]:
    """读取指定 Scheduled Trigger 已产生的真实 Execution。"""
    engine = _test_engine()
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT id, status, idempotency_key, input_data FROM workflow_executions WHERE idempotency_key LIKE :prefix ORDER BY created_at ASC"),
                {"prefix": f"scheduled:{trigger_id}:%"},
            )
            return [dict(row._mapping) for row in result]
    finally:
        await engine.dispose()


async def _governance_rows(execution_id: str) -> tuple[list[dict], list[dict]]:
    """读取真实 PostgreSQL 中与 Execution 绑定的 Audit/Trace 记录。"""
    engine = _test_engine()
    try:
        async with engine.connect() as connection:
            audit = await connection.execute(
                text("SELECT tenant_id, workflow_id, workflow_execution_id, action, status, metadata FROM audit_logs WHERE workflow_execution_id = :execution_id ORDER BY created_at ASC"),
                {"execution_id": uuid.UUID(execution_id)},
            )
            trace = await connection.execute(
                text("SELECT tenant_id, workflow_id, execution_id, event_type, status, data FROM workflow_trace_events WHERE execution_id = :execution_id ORDER BY created_at ASC"),
                {"execution_id": uuid.UUID(execution_id)},
            )
            return [dict(row._mapping) for row in audit], [dict(row._mapping) for row in trace]
    finally:
        await engine.dispose()


async def _seed_scheduler_backlog(trigger_id: str, next_run_at: datetime, interval_seconds: int) -> None:
    """把 API 创建的唯一 Schedule 构造成明确到期事实。"""
    engine = _test_engine()
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("UPDATE workflow_schedules SET next_run_at = :next_run_at, schedule_expression = :schedule_expression, misfire_policy = 'catch_up', catch_up_limit = 2, updated_at = :updated_at WHERE trigger_id = :trigger_id"),
                {"trigger_id": uuid.UUID(trigger_id), "schedule_expression": f"interval:{interval_seconds}", "next_run_at": next_run_at.replace(tzinfo=None), "updated_at": datetime.now(UTC).replace(tzinfo=None)},
            )
    finally:
        await engine.dispose()


def _wait_for_trigger_execution(loop: asyncio.AbstractEventLoop, trigger_id: str, timeout_seconds: float = 20.0) -> list[dict]:
    """轮询指定 Trigger 的真实 Execution，直到进入终态或超时。"""
    deadline = time.monotonic() + timeout_seconds
    terminal = {"completed", "failed", "cancelled"}
    while time.monotonic() < deadline:
        rows = _run_async(loop, _scheduled_execution_rows(trigger_id))
        if rows and all(row["status"] in terminal for row in rows):
            return rows
        time.sleep(1.0)
    return _run_async(loop, _scheduled_execution_rows(trigger_id))


def _wait_for_execution(loop: asyncio.AbstractEventLoop, key: str, timeout_seconds: float = 20.0) -> list[dict]:
    """轮询指定幂等键的 Execution，直到进入终态或超时。"""
    deadline = time.monotonic() + timeout_seconds
    terminal = {"completed", "failed", "cancelled"}
    while time.monotonic() < deadline:
        rows = _run_async(loop, _execution_rows(key))
        if rows and all(row["status"] in terminal for row in rows):
            return rows
        time.sleep(1.0)
    return _run_async(loop, _execution_rows(key))


def _create_scheduled_trigger(client: httpx.Client, name: str, config: dict) -> dict:
    """通过正式 Trigger API 创建测试 Scheduled Trigger。"""
    return _request(client, "POST", f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers", json={"name": name, "trigger_type": "scheduled", "config": config}).json()


def test_scheduled_trigger_create_update_invoke_and_runtime_contract_real_http(scheduler_event_loop):
    """验证 Scheduled Trigger 配置、禁止手工 invoke、真实 Execution 与治理关联。"""
    name = f"api-real-scheduled-{uuid.uuid4().hex[:8]}"
    config = {"timezone": "Asia/Shanghai", "interval_seconds": 60}
    updated_config = {"timezone": "UTC", "interval_seconds": 60}
    expected_config = {**config, "misfire_policy": "skip", "catch_up_limit": 10}
    expected_updated_config = {**updated_config, "misfire_policy": "skip", "catch_up_limit": 10}
    with _client() as client:
        trigger = _create_scheduled_trigger(client, name, config)
        trigger_id = trigger["id"]
        assert trigger["trigger_type"] == "scheduled"
        assert trigger["status"] == "enabled"
        assert trigger["config"] == expected_config
        assert _request(client, "GET", f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}").json()["config"] == expected_config
        updated = _request(client, "PATCH", f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}", json={"config": updated_config}).json()
        assert updated["config"] == expected_updated_config
        invalid = client.patch(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}", json={"config": {"timezone": "Not/A_Timezone", "interval_seconds": 300}})
        assert invalid.status_code == 422, invalid.text
        invoke = client.post(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}/invoke", json={"input_data": {"source": "scheduled-real-api"}})
        assert invoke.status_code == 409, invoke.text
        assert "不可直接调用" in invoke.text
        _run_async(scheduler_event_loop, _seed_scheduler_backlog(trigger_id, datetime.now(UTC), 60))
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
        assert audit_rows and trace_rows
        assert all(row["tenant_id"] is not None for row in audit_rows + trace_rows)
        assert all(row["workflow_id"] == uuid.UUID(TRIGGER_WORKFLOW_ID) for row in audit_rows + trace_rows)
        assert all(row["workflow_execution_id"] == rows[0]["id"] for row in audit_rows)
        assert all(row["execution_id"] == rows[0]["id"] for row in trace_rows)
        assert any(row["action"] == "workflow.trigger.scheduled" for row in audit_rows)
        assert any(row["event_type"] == "trigger.scheduled" for row in trace_rows)
        time.sleep(2)
        assert len(_run_async(scheduler_event_loop, _execution_rows(runtime_key))) == 1
        assert _request(client, "PATCH", f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}", json={"status": "disabled"}).status_code == 200
        assert client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}").status_code == 204
        assert client.get(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}").status_code == 404


def test_scheduled_trigger_two_workers_converge_on_one_slot_execution_real_http(scheduler_event_loop):
    """验证两个 Scheduler 实例对同一持久化 slot 只能产生一个 Execution。"""
    engine, session_factory = _test_session_factory()
    with _client() as client:
        trigger = _create_scheduled_trigger(client, f"api-real-scheduled-workers-{uuid.uuid4().hex[:8]}", {"timezone": "UTC", "interval_seconds": 60})
        trigger_id = trigger["id"]
        now = datetime.now(UTC).replace(microsecond=0)
        runtime_key = ScheduledTriggerScheduler.idempotency_key(trigger_id, now, 60)
        try:
            _run_async(scheduler_event_loop, _seed_scheduler_backlog(trigger_id, now, 60))
            async def dispatch():
                first = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=1, session_factory=session_factory)
                second = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=1, session_factory=session_factory)
                return await asyncio.gather(first.tick_once(now), second.tick_once(now))
            counters = _run_async(scheduler_event_loop, dispatch())
            rows = _wait_for_execution(scheduler_event_loop, runtime_key)
            assert len(rows) == 1, rows
            assert rows[0]["idempotency_key"] == runtime_key
            assert rows[0]["input_data"]["scheduled_slot"] == ScheduledTriggerScheduler.interval_slot(now, 60)
            assert rows[0]["input_data"]["recovery"] is False
            assert sum(item["dispatched"] for item in counters) == 1
        finally:
            client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
            _run_async(scheduler_event_loop, engine.dispose())


def test_scheduled_trigger_recovery_slot_persists_execution_metadata_real_http(scheduler_event_loop):
    """验证历史 misfire slot 与当前 slot 的 Execution 元数据及幂等恢复。"""
    engine, session_factory = _test_session_factory()
    config = {"timezone": "UTC", "interval_seconds": 60, "misfire_policy": "catch_up", "catch_up_limit": 2}
    with _client() as client:
        trigger = _create_scheduled_trigger(client, f"api-real-scheduled-recovery-{uuid.uuid4().hex[:8]}", config)
        trigger_id = trigger["id"]
        scheduler = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=2, session_factory=session_factory)
        now = datetime.now(UTC).replace(microsecond=0)
        current_slot = scheduler.interval_slot(now, 60)
        recovery_slot = current_slot - 1
        recovery_key = scheduler.slot_idempotency_key(trigger_id, recovery_slot)
        current_key = scheduler.slot_idempotency_key(trigger_id, current_slot)
        try:
            recovery_time = datetime.fromtimestamp(recovery_slot * 60, UTC)
            _run_async(scheduler_event_loop, _seed_scheduler_backlog(trigger_id, recovery_time, 60))
            counters = _run_async(scheduler_event_loop, scheduler.tick_once(now))
            recovery_rows = _wait_for_execution(scheduler_event_loop, recovery_key)
            current_rows = _wait_for_execution(scheduler_event_loop, current_key)
            assert counters["recovered"] >= 1, counters
            assert len(recovery_rows) == len(current_rows) == 1
            assert recovery_rows[0]["status"] == current_rows[0]["status"] == "completed"
            assert recovery_rows[0]["input_data"]["scheduled_slot"] == recovery_slot
            assert recovery_rows[0]["input_data"]["recovery"] is True
            assert current_rows[0]["input_data"]["scheduled_slot"] == current_slot
            assert current_rows[0]["input_data"]["recovery"] is False
            assert "planned_at" in recovery_rows[0]["input_data"] and "planned_at" in current_rows[0]["input_data"]
            restarted = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=2, session_factory=session_factory)
            second_counters = _run_async(scheduler_event_loop, restarted.tick_once(now))
            assert second_counters["dispatched"] == 0, second_counters
            assert len(_run_async(scheduler_event_loop, _execution_rows(recovery_key))) == 1
            assert len(_run_async(scheduler_event_loop, _execution_rows(current_key))) == 1
        finally:
            client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
            _run_async(scheduler_event_loop, engine.dispose())
