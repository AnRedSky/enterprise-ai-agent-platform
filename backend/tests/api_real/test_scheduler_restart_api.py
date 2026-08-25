"""真实 Scheduler / Worker 恢复验收。

本测试只验证真实 HTTP + PostgreSQL + 已由开发者手动启动的 Scheduler/Worker 链路。
测试本身禁止创建、停止或重启任何服务进程；实际进程生命周期切换由本地人工操作完成。
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler

TOKEN = os.getenv("ACCESS_TOKEN")
BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
pytestmark = pytest.mark.real_api


async def _schedule_row(trigger_id: str) -> dict | None:
    """读取真实 PostgreSQL 中 Scheduler 的持久化状态。"""
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


async def _seed_recovery_slot(trigger_id: str, planned_at: datetime) -> None:
    """将真实持久化 Schedule 设置为历史待恢复 slot，不启动任何服务。"""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
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
    """读取指定恢复 slot 的真实 WorkflowExecution。"""
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


def _wait_for_execution(idempotency_key: str, timeout_seconds: float = 20.0) -> list[dict]:
    """轮询真实 PostgreSQL，等待已运行 Worker 消费恢复 Execution。"""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        rows = asyncio.run(_execution_rows(idempotency_key))
        if rows and all(row["status"] in {"completed", "failed", "cancelled"} for row in rows):
            return rows
        time.sleep(0.5)
    return asyncio.run(_execution_rows(idempotency_key))


def _create_restart_fixture() -> tuple[str, str]:
    """通过真实 API 创建本验收专属 Workflow 与 Scheduled Trigger。"""
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for scheduler recovery validation")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=10.0) as client:
        workflow = client.post(
            "/workflows",
            json={
                "name": f"Scheduler Worker Acceptance {uuid4().hex[:8]}",
                "description": "真实 Scheduler/Worker 恢复验收专用 Workflow",
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
        version_id = version.json()["id"]
        published = client.post(f"/workflows/{workflow_id}/versions/{version_id}/publish")
        assert published.status_code == 200, published.text

        trigger = client.post(
            f"/workflows/{workflow_id}/triggers",
            json={
                "name": f"restart-{uuid4().hex[:8]}",
                "trigger_type": "scheduled",
                "config": {"timezone": "UTC", "interval_seconds": 60, "misfire_policy": "fire_once"},
            },
        )
        assert trigger.status_code == 201, trigger.text
        return str(workflow_id), str(trigger.json()["id"])


def test_scheduled_trigger_recovers_persisted_slot_with_external_services():
    """验证已手动运行的 Scheduler/Worker 能消费 PostgreSQL 中持久化的恢复 slot。"""
    workflow_id, trigger_id = _create_restart_fixture()
    interval_seconds = 60
    planned_at = datetime.now(UTC).replace(microsecond=0) - timedelta(seconds=2 * interval_seconds)

    try:
        asyncio.run(_seed_recovery_slot(trigger_id, planned_at))
        schedule = asyncio.run(_schedule_row(trigger_id))
        assert schedule is not None
        assert schedule["enabled"] is True

        runtime_key = ScheduledTriggerScheduler.idempotency_key(trigger_id, planned_at, interval_seconds)
        rows = _wait_for_execution(runtime_key)
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "completed", rows
        assert rows[0]["input_data"]["scheduled_slot"] == ScheduledTriggerScheduler.interval_slot(
            planned_at, interval_seconds
        )
        assert rows[0]["input_data"]["recovery"] is True

        duplicate_rows = _wait_for_execution(runtime_key, timeout_seconds=3)
        assert len(duplicate_rows) == 1, duplicate_rows
    finally:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        with httpx.Client(base_url=BASE_URL, headers=headers, timeout=10.0) as client:
            response = client.delete(f"/workflows/{workflow_id}/triggers/{trigger_id}")
            assert response.status_code in {204, 404}, response.text
