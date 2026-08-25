"""真实 Scheduler / Worker Service 重启验收：验证调度与执行跨进程解耦并保持持久化恢复。"""

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
    """申请当前空闲的本地 TCP 端口，仅用于临时 API fixture bootstrap。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_api(port: int) -> subprocess.Popen:
    """启动仅用于 HTTP fixture bootstrap/cleanup 的 API Service。"""
    return subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _start_scheduler() -> subprocess.Popen:
    """启动真实独立 Scheduler Service；不启动 HTTP API 或 Worker。"""
    return subprocess.Popen(["uv", "run", "python", "run_scheduler.py"], cwd=BACKEND_DIR,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _start_worker() -> subprocess.Popen:
    """启动真实独立 Worker Service；只消费 PostgreSQL pending Execution。"""
    return subprocess.Popen(["uv", "run", "python", "run_worker.py"], cwd=BACKEND_DIR,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _wait_for_api(process: subprocess.Popen, port: int, timeout_seconds: float = 20.0) -> None:
    """等待 fixture API 健康。"""
    deadline = time.monotonic() + timeout_seconds
    with httpx.Client(timeout=2.0) as client:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(f"API Service 进程提前退出，exit_code={process.returncode}")
            try:
                if client.get(f"http://127.0.0.1:{port}/health").status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
    raise AssertionError(f"API Service 在 {timeout_seconds}s 内未就绪")


def _wait_for_background_service(process: subprocess.Popen, service_name: str, timeout_seconds: float = 5.0) -> None:
    """确认独立后台服务保持运行。"""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"{service_name} 进程提前退出，exit_code={process.returncode}")
        time.sleep(0.25)


def _stop_process(process: subprocess.Popen) -> None:
    """停止真实服务进程并避免本地遗留后台进程。"""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


async def _schedule_row(trigger_id: str) -> dict | None:
    """读取真实 PostgreSQL Scheduler 状态。"""
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
    """停止 Scheduler 后，将真实持久化状态回拨到待恢复的历史 slot。"""
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
                {"trigger_id": UUID(trigger_id), "planned_at": planned_at.astimezone(UTC).replace(tzinfo=None),
                 "updated_at": datetime.now(UTC).replace(tzinfo=None)},
            )
            if updated.rowcount != 1:
                raise AssertionError(f"Scheduler 状态回拨失败，trigger_id={trigger_id}")
    finally:
        await engine.dispose()


async def _execution_rows(idempotency_key: str) -> list[dict]:
    """读取指定 Scheduler slot 的真实 WorkflowExecution。"""
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
    """读取恢复执行关联的 AuditLog 与 WorkflowTraceEvent。"""
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
    """轮询真实 PostgreSQL，等待 Worker 执行结果进入终态。"""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        rows = asyncio.run(_execution_rows(idempotency_key))
        if rows and all(row["status"] in {"completed", "failed", "cancelled"} for row in rows):
            return rows
        time.sleep(0.5)
    return asyncio.run(_execution_rows(idempotency_key))


def _create_restart_fixture(base_url: str, token: str) -> tuple[str, str]:
    """通过真实 API 创建本 Acceptance 专属的可执行 Workflow 与 Scheduled Trigger。"""
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
        workflow = client.post("/workflows", json={
            "name": f"Scheduler Worker Acceptance {uuid4().hex[:8]}",
            "description": "真实 Scheduler/Worker 解耦验收专用 Workflow",
        })
        assert workflow.status_code == 201, workflow.text
        workflow_id = workflow.json()["id"]

        version = client.post(f"/workflows/{workflow_id}/versions", json={
            "definition": {
                "nodes": [
                    {"id": "input", "type": "input", "config": {}},
                    {"id": "output", "type": "output", "config": {}},
                ],
                "edges": [],
            }
        })
        assert version.status_code == 201, version.text
        version_payload = version.json()
        published = client.post(f"/workflows/{workflow_id}/versions/{version_payload['id']}/publish")
        assert published.status_code == 200, published.text

        trigger = client.post(f"/workflows/{workflow_id}/triggers", json={
            "name": f"restart-{uuid4().hex[:8]}",
            "trigger_type": "scheduled",
            "config": {"timezone": "UTC", "interval_seconds": 60, "misfire_policy": "fire_once"},
        })
        assert trigger.status_code == 201, trigger.text
        trigger_id = trigger.json()["id"]
        disabled = client.patch(f"/workflows/{workflow_id}/triggers/{trigger_id}", json={"status": "disabled"})
        assert disabled.status_code == 200, disabled.text
    return str(workflow_id), str(trigger_id)


def test_scheduled_trigger_recovers_after_real_service_restart():
    """验证 Scheduler 只产生 Execution，Worker 跨进程消费并完成历史 slot。"""
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for scheduler restart validation")

    bootstrap_port = _free_port()
    base_url = f"http://127.0.0.1:{bootstrap_port}/api/v1"
    api_process = _start_api(bootstrap_port)
    scheduler_process: subprocess.Popen | None = None
    worker_process: subprocess.Popen | None = None
    workflow_id: str | None = None
    trigger_id: str | None = None
    interval_seconds = 60
    planned_at = datetime.now(UTC).replace(microsecond=0) - timedelta(seconds=2 * interval_seconds)

    try:
        _wait_for_api(api_process, bootstrap_port)
        workflow_id, trigger_id = _create_restart_fixture(base_url, TOKEN)
        _stop_process(api_process)
        api_process = None

        # 第一阶段只启动 Scheduler：验证 schedule 持久化，但没有 Worker 时不得直接执行 Workflow。
        scheduler_process = _start_scheduler()
        _wait_for_background_service(scheduler_process, "Scheduler Service")
        deadline = time.monotonic() + 15
        schedule = None
        while time.monotonic() < deadline:
            schedule = asyncio.run(_schedule_row(trigger_id))
            if schedule is not None:
                break
            if scheduler_process.poll() is not None:
                raise AssertionError(f"Scheduler Service 提前退出，exit_code={scheduler_process.returncode}")
            time.sleep(0.5)
        assert schedule is not None, "首次独立 Scheduler Service 生命周期未创建 WorkflowSchedule 持久化状态"
        assert schedule["enabled"] is False

        _stop_process(scheduler_process)
        scheduler_process = None
        asyncio.run(_seed_restart_slot(trigger_id, planned_at))
        runtime_key = ScheduledTriggerScheduler.idempotency_key(trigger_id, planned_at, interval_seconds)

        # 第二阶段同时启动独立 Scheduler + Worker：Scheduler 只入队，Worker 才执行。
        scheduler_process = _start_scheduler()
        worker_process = _start_worker()
        _wait_for_background_service(scheduler_process, "Scheduler Service")
        _wait_for_background_service(worker_process, "Worker Service")

        rows = _wait_for_execution(runtime_key)
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "completed", rows
        assert rows[0]["input_data"]["scheduled_slot"] == ScheduledTriggerScheduler.interval_slot(planned_at, interval_seconds)
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
        if worker_process is not None:
            _stop_process(worker_process)
        if scheduler_process is not None:
            _stop_process(scheduler_process)
        if api_process is not None:
            _stop_process(api_process)
        if workflow_id and trigger_id:
            cleanup_process = _start_api(bootstrap_port)
            try:
                _wait_for_api(cleanup_process, bootstrap_port)
                with httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=10.0) as client:
                    response = client.delete(f"/workflows/{workflow_id}/triggers/{trigger_id}")
                    assert response.status_code in {204, 404}, response.text
            finally:
                _stop_process(cleanup_process)
