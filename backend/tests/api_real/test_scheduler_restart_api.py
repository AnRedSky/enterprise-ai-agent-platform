"""真实服务重启验收：验证 Scheduler 持久化状态可跨进程恢复，并保持治理关联。"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler

TOKEN = os.getenv("ACCESS_TOKEN")
TRIGGER_WORKFLOW_ID = os.getenv("TRIGGER_WORKFLOW_ID")
BACKEND_DIR = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.real_api


async def _schedule_row(trigger_id: str) -> dict | None:
    """读取真实 PostgreSQL 中的 Scheduler 状态，用于确认进程停止前已经完成持久化初始化。

    参数：
        trigger_id: Scheduled Trigger 的 UUID 字符串。

    返回值：
        Scheduler 状态行；不存在时返回 None。
    """
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT id, tenant_id, workflow_id, next_run_at, lease_owner, lease_expires_at "
                    "FROM workflow_schedules WHERE trigger_id = :trigger_id"
                ),
                {"trigger_id": UUID(trigger_id)},
            )
            row = result.mappings().one_or_none()
            return dict(row) if row else None
    finally:
        await engine.dispose()


async def _seed_restart_slot(trigger_id: str, planned_at: datetime) -> None:
    """把已持久化 Scheduler 的 next_run_at 回拨到历史槽位，模拟真实服务停止期间的到期任务。

    参数：
        trigger_id: Scheduled Trigger 的 UUID 字符串。
        planned_at: 重启后应恢复执行的历史计划时间。

    返回值：
        无；函数直接更新 PostgreSQL 中的 Scheduler 状态。
    """
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE workflow_schedules "
                    "SET next_run_at = :planned_at, lease_owner = NULL, lease_expires_at = NULL, "
                    "updated_at = :updated_at "
                    "WHERE trigger_id = :trigger_id"
                ),
                {
                    "trigger_id": UUID(trigger_id),
                    "planned_at": planned_at.astimezone(UTC).replace(tzinfo=None),
                    "updated_at": datetime.now(UTC).replace(tzinfo=None),
                },
            )
    finally:
        await engine.dispose()


async def _execution_rows(idempotency_key: str) -> list[dict]:
    """读取指定 Scheduler slot 的真实 WorkflowExecution，确认跨进程恢复只产生一个执行。

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
                    "SELECT id, tenant_id, workflow_id, status, idempotency_key, input_data "
                    "FROM workflow_executions WHERE idempotency_key = :idempotency_key ORDER BY created_at ASC"
                ),
                {"idempotency_key": idempotency_key},
            )
            return [dict(row) for row in result.mappings()]
    finally:
        await engine.dispose()


async def _governance_rows(execution_id: str) -> tuple[list[dict], list[dict]]:
    """读取真实 PostgreSQL 中与恢复执行关联的 AuditLog 与 WorkflowTraceEvent。

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
                    "SELECT tenant_id, workflow_id, workflow_execution_id, action, status "
                    "FROM audit_logs WHERE workflow_execution_id = :execution_id ORDER BY created_at ASC"
                ),
                {"execution_id": UUID(execution_id)},
            )
            trace_result = await connection.execute(
                text(
                    "SELECT tenant_id, workflow_id, execution_id, event_type, status "
                    "FROM workflow_trace_events WHERE execution_id = :execution_id ORDER BY created_at ASC"
                ),
                {"execution_id": UUID(execution_id)},
            )
            return [dict(row) for row in audit_result.mappings()], [dict(row) for row in trace_result.mappings()]
    finally:
        await engine.dispose()


def _free_port() -> int:
    """申请一个当前可用的本地 TCP 端口，避免重启验收固定依赖开发机端口状态。

    返回值：
        当前探测为空闲的 TCP 端口。
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server(port: int) -> subprocess.Popen:
    """启动真实 Uvicorn 进程，使 Scheduler 生命周期由真实进程负责。

    参数：
        port: Uvicorn 监听的本地 TCP 端口。

    返回值：
        已启动但尚未确认健康状态的子进程对象。
    """
    return subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_health(process: subprocess.Popen, base_url: str, timeout_seconds: float = 20.0) -> None:
    """等待真实 HTTP 服务进入可访问状态，超时或提前退出均立即失败。

    参数：
        process: Uvicorn 子进程。
        base_url: 服务根 URL。
        timeout_seconds: 最大等待秒数。

    返回值：
        服务健康检查成功后返回 None。
    """
    deadline = time.monotonic() + timeout_seconds
    with httpx.Client(timeout=2.0) as client:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(f"真实 Uvicorn 进程提前退出，exit_code={process.returncode}")
            try:
                response = client.get(f"{base_url}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
    raise AssertionError(f"真实 HTTP 服务在 {timeout_seconds}s 内未就绪: {base_url}")


def _stop_server(process: subprocess.Popen) -> None:
    """停止真实 Uvicorn 进程，并确保 Windows 本地验收不会遗留后台进程。

    参数：
        process: 待停止的 Uvicorn 子进程。

    返回值：
        无；进程正常退出或被强制终止后返回。
    """
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _wait_for_execution(idempotency_key: str, timeout_seconds: float = 20.0) -> list[dict]:
    """轮询真实 PostgreSQL，等待恢复 slot 的 Execution 进入终态。

    参数：
        idempotency_key: 目标 Scheduler slot 的统一幂等键。
        timeout_seconds: 最大等待秒数。

    返回值：
        当前数据库中该幂等键对应的全部 Execution 行。
    """
    import asyncio

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        rows = asyncio.run(_execution_rows(idempotency_key))
        if rows and all(row["status"] in {"completed", "failed", "cancelled"} for row in rows):
            return rows
        time.sleep(0.5)
    return asyncio.run(_execution_rows(idempotency_key))


def test_scheduled_trigger_recovers_after_real_service_restart():
    """验证 Scheduler 在真实进程停止/重启后从 PostgreSQL 恢复历史 slot。

    验证范围：真实 HTTP、真实 Uvicorn 生命周期、真实 PostgreSQL Scheduler 状态、slot 幂等、
    WorkflowExecution 以及 Audit/Trace tenant/workflow/execution 关联；不使用进程内 Scheduler 重建替代服务重启。
    """
    import asyncio

    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for scheduler restart validation")
    if not TRIGGER_WORKFLOW_ID:
        pytest.fail("TRIGGER_WORKFLOW_ID is required for scheduler restart validation")

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}/api/v1"
    process = _start_server(port)
    trigger_id: str | None = None
    interval_seconds = 60
    planned_at = datetime.now(UTC).replace(microsecond=0) - timedelta(seconds=2 * interval_seconds)
    runtime_key: str | None = None

    try:
        _wait_for_health(process, f"http://127.0.0.1:{port}")
        headers = {"Authorization": f"Bearer {TOKEN}"}
        with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
            created = client.post(
                f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers",
                json={
                    "name": f"api-real-restart-{uuid4().hex[:8]}",
                    "trigger_type": "scheduled",
                    "config": {
                        "timezone": "UTC",
                        "interval_seconds": interval_seconds,
                        "misfire_policy": "fire_once",
                    },
                },
            )
            assert created.status_code == 201, created.text
            trigger_id = created.json()["id"]

        deadline = time.monotonic() + 15
        schedule = None
        while time.monotonic() < deadline:
            schedule = asyncio.run(_schedule_row(trigger_id))
            if schedule is not None:
                break
            time.sleep(0.5)
        assert schedule is not None, "首次真实服务生命周期未创建 WorkflowSchedule 持久化状态"

        # 先停止真实进程，再回拨 PostgreSQL 状态；这样重启前不会由原进程抢先消费目标历史槽位。
        _stop_server(process)
        asyncio.run(_seed_restart_slot(trigger_id, planned_at))
        runtime_key = ScheduledTriggerScheduler.idempotency_key(trigger_id, planned_at, interval_seconds)

        process = _start_server(port)
        _wait_for_health(process, f"http://127.0.0.1:{port}")
        rows = _wait_for_execution(runtime_key)
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "completed", rows
        assert rows[0]["input_data"]["scheduled_slot"] == ScheduledTriggerScheduler.interval_slot(
            planned_at, interval_seconds
        )
        assert rows[0]["input_data"]["recovery"] is True

        audit_rows, trace_rows = asyncio.run(_governance_rows(str(rows[0]["id"])))
        assert audit_rows, "重启恢复 Execution 必须存在真实 AuditLog"
        assert trace_rows, "重启恢复 Execution 必须存在真实 WorkflowTraceEvent"
        assert all(row["tenant_id"] is not None for row in audit_rows + trace_rows)
        assert all(row["workflow_id"] == UUID(TRIGGER_WORKFLOW_ID) for row in audit_rows + trace_rows)
        assert all(row["workflow_execution_id"] == rows[0]["id"] for row in audit_rows)
        assert all(row["execution_id"] == rows[0]["id"] for row in trace_rows)

        duplicate_rows = _wait_for_execution(runtime_key, timeout_seconds=3)
        assert len(duplicate_rows) == 1, duplicate_rows
    finally:
        _stop_server(process)
        if trigger_id:
            cleanup_process = _start_server(port)
            try:
                _wait_for_health(cleanup_process, f"http://127.0.0.1:{port}")
                if TOKEN:
                    with httpx.Client(
                        base_url=base_url,
                        headers={"Authorization": f"Bearer {TOKEN}"},
                        timeout=10.0,
                    ) as client:
                        response = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
                        assert response.status_code in {204, 404}, response.text
            finally:
                _stop_server(cleanup_process)
