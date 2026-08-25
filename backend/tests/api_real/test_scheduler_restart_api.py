"""真实服务重启验收：验证 Scheduler 持久化状态可跨进程恢复，并保持治理关联。"""

from __future__ import annotations

import asyncio
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
BACKEND_DIR = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.real_api


def _free_port() -> int:
    """申请当前空闲的本地 TCP 端口，避免真实生命周期验收依赖固定端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server(port: int) -> subprocess.Popen:
    """启动真实 Uvicorn 进程，使 Scheduler 生命周期由真实进程负责。

    Args:
        port: Uvicorn 监听端口。

    Returns:
        已启动但尚未完成健康检查的真实 Uvicorn 子进程。
    """
    return subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_health(process: subprocess.Popen, base_url: str, timeout_seconds: float = 20.0) -> None:
    """等待真实 HTTP 服务健康；进程提前退出或超时均立即失败。"""
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
    """停止真实 Uvicorn 进程，并确保 Windows 本地验收不遗留后台进程。"""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


async def _schedule_row(trigger_id: str) -> dict | None:
    """读取真实 PostgreSQL Scheduler 状态，确认首次生命周期已经完成持久化初始化。"""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT id, tenant_id, workflow_id, next_run_at, enabled, status, lease_owner, lease_expires_at "
                    "FROM workflow_schedules WHERE trigger_id = :trigger_id"
                ),
                {"trigger_id": UUID(trigger_id)},
            )
            row = result.mappings().one_or_none()
            return dict(row) if row else None
    finally:
        await engine.dispose()


async def _seed_restart_slot(trigger_id: str, planned_at: datetime) -> None:
    """回拨真实 Scheduler 状态到历史槽位，并在重启前激活目标 Trigger。

    Args:
        trigger_id: Scheduled Trigger UUID 字符串。
        planned_at: 重启后应恢复执行的历史计划时间。

    Returns:
        无；直接修改真实 PostgreSQL 测试状态。

    设计意图：首次生命周期阶段把 Trigger 置为 disabled，确保 Scheduler 只负责建立持久化状态而不会
    在停止前抢先执行。停止进程后再一次性把 Trigger 与 Schedule 激活并回拨历史 slot，使重启后的
    Scheduler 成为唯一能够消费目标 slot 的 worker。
    """
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE workflow_triggers SET status = 'enabled', updated_at = :updated_at "
                    "WHERE id = :trigger_id"
                ),
                {"trigger_id": UUID(trigger_id), "updated_at": datetime.now(UTC).replace(tzinfo=None)},
            )
            updated = await connection.execute(
                text(
                    "UPDATE workflow_schedules SET enabled = TRUE, status = 'enabled', next_run_at = :planned_at, "
                    "lease_owner = NULL, lease_expires_at = NULL, updated_at = :updated_at "
                    "WHERE trigger_id = :trigger_id"
                ),
                {
                    "trigger_id": UUID(trigger_id),
                    "planned_at": planned_at.astimezone(UTC).replace(tzinfo=None),
                    "updated_at": datetime.now(UTC).replace(tzinfo=None),
                },
            )
            if updated.rowcount != 1:
                raise AssertionError(f"Scheduler 状态回拨失败，trigger_id={trigger_id}")
    finally:
        await engine.dispose()


async def _execution_rows(idempotency_key: str) -> list[dict]:
    """读取指定 Scheduler slot 的真实 WorkflowExecution，确认跨进程恢复只产生一个执行。"""
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
    """读取恢复执行关联的真实 AuditLog 与 WorkflowTraceEvent。"""
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


def _wait_for_execution(idempotency_key: str, timeout_seconds: float = 20.0) -> list[dict]:
    """轮询真实 PostgreSQL，等待恢复 slot 的 Execution 进入终态。"""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        rows = asyncio.run(_execution_rows(idempotency_key))
        if rows and all(row["status"] in {"completed", "failed", "cancelled"} for row in rows):
            return rows
        time.sleep(0.5)
    return asyncio.run(_execution_rows(idempotency_key))


def _create_restart_fixture(base_url: str, token: str) -> tuple[str, str]:
    """通过真实 HTTP 创建本 Acceptance 专属的可执行 Workflow 与 Scheduled Trigger。

    Args:
        base_url: 临时真实 API 的 `/api/v1` 地址。
        token: Tenant-safe Real API 管理员访问令牌。

    Returns:
        `(workflow_id, trigger_id)`，均来自真实 HTTP 持久化响应。

    设计意图：restart acceptance 不再依赖通用 Real API bootstrap 的 Workflow ID，避免共享测试夹具
    被其他场景复用、历史无效 Workflow 污染或旧 context 导致本验收失去确定性。Workflow Version 在
    发布后立即通过 HTTP GET 再验证 `nodes` 非空，保证 Scheduler 验收使用的执行定义满足 Runtime Contract。
    """
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
        workflow = client.post(
            "/workflows",
            json={
                "name": f"Scheduler Restart Acceptance {uuid4().hex[:8]}",
                "description": "真实 Scheduler restart acceptance 专用可执行 Workflow",
            },
        )
        assert workflow.status_code == 201, workflow.text
        workflow_id = workflow.json()["id"]

        version = client.post(
            f"/workflows/{workflow_id}/versions",
            json={
                "definition": {
                    "nodes": [
                        {"id": "input", "type": "input", "config": {}},
                        {"id": "output", "type": "output", "config": {}},
                    ],
                    "edges": [],
                }
            },
        )
        assert version.status_code == 201, version.text
        version_payload = version.json()
        assert version_payload["definition"]["nodes"], version_payload

        published = client.post(f"/workflows/{workflow_id}/versions/{version_payload['id']}/publish")
        assert published.status_code == 200, published.text

        persisted_version = client.get(f"/workflows/{workflow_id}/versions/{version_payload['id']}")
        assert persisted_version.status_code == 200, persisted_version.text
        persisted_definition = persisted_version.json()["definition"]
        assert persisted_definition.get("nodes"), persisted_version.json()

        trigger = client.post(
            f"/workflows/{workflow_id}/triggers",
            json={
                "name": f"restart-{uuid4().hex[:8]}",
                "trigger_type": "scheduled",
                "config": {
                    "timezone": "UTC",
                    "interval_seconds": 60,
                    "misfire_policy": "fire_once",
                },
            },
        )
        assert trigger.status_code == 201, trigger.text
        trigger_id = trigger.json()["id"]

        # 立即禁用 Trigger：首次 Scheduler 生命周期仍需初始化 WorkflowSchedule，但不得抢先消费 slot。
        disabled = client.patch(
            f"/workflows/{workflow_id}/triggers/{trigger_id}",
            json={"status": "disabled"},
        )
        assert disabled.status_code == 200, disabled.text

    return str(workflow_id), str(trigger_id)


def test_scheduled_trigger_recovers_after_real_service_restart():
    """验证 Scheduler 在真实进程停止/重启后从 PostgreSQL 恢复历史 slot。"""
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for scheduler restart validation")

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}/api/v1"
    process = _start_server(port)
    workflow_id: str | None = None
    trigger_id: str | None = None
    interval_seconds = 60
    planned_at = datetime.now(UTC).replace(microsecond=0) - timedelta(seconds=2 * interval_seconds)
    runtime_key: str | None = None

    try:
        _wait_for_health(process, f"http://127.0.0.1:{port}")
        workflow_id, trigger_id = _create_restart_fixture(base_url, TOKEN)

        deadline = time.monotonic() + 15
        schedule = None
        while time.monotonic() < deadline:
            schedule = asyncio.run(_schedule_row(trigger_id))
            if schedule is not None:
                break
            time.sleep(0.5)
        assert schedule is not None, "首次真实服务生命周期未创建 WorkflowSchedule 持久化状态"
        assert schedule["enabled"] is False

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
        assert all(row["workflow_id"] == UUID(workflow_id) for row in audit_rows + trace_rows)
        assert all(row["workflow_execution_id"] == rows[0]["id"] for row in audit_rows)
        assert all(row["execution_id"] == rows[0]["id"] for row in trace_rows)

        duplicate_rows = _wait_for_execution(runtime_key, timeout_seconds=3)
        assert len(duplicate_rows) == 1, duplicate_rows
    finally:
        _stop_server(process)
        if workflow_id and trigger_id:
            cleanup_process = _start_server(port)
            try:
                _wait_for_health(cleanup_process, f"http://127.0.0.1:{port}")
                with httpx.Client(
                    base_url=base_url,
                    headers={"Authorization": f"Bearer {TOKEN}"} if TOKEN else {},
                    timeout=10.0,
                ) as client:
                    response = client.delete(f"/workflows/{workflow_id}/triggers/{trigger_id}")
                    assert response.status_code in {204, 404}, response.text
            finally:
                _stop_server(cleanup_process)
