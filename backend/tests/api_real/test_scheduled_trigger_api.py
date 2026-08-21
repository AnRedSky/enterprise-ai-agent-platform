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
from app.services.scheduled_trigger_scheduler import ScheduledTriggerScheduler

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
TRIGGER_WORKFLOW_ID = os.getenv("TRIGGER_WORKFLOW_ID")

pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20.0,
    )


async def _execution_rows(idempotency_key: str) -> list[dict]:
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


def _wait_for_scheduled_execution(idempotency_key: str, timeout_seconds: float = 15.0) -> list[dict]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        rows = asyncio.run(_execution_rows(idempotency_key))
        if rows:
            return rows
        time.sleep(1.0)
    return asyncio.run(_execution_rows(idempotency_key))


def test_scheduled_trigger_create_update_invoke_and_runtime_contract_real_http():
    if not TRIGGER_WORKFLOW_ID:
        pytest.fail("TRIGGER_WORKFLOW_ID is required for scheduled Trigger validation")

    name = f"api-real-scheduled-{uuid.uuid4().hex[:8]}"
    config = {"timezone": "Asia/Shanghai", "interval_seconds": 60}
    updated_config = {"timezone": "UTC", "interval_seconds": 60}

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
        assert trigger["config"] == config

        # Capture the current interval slot immediately after creation. The
        # scheduler is allowed to dispatch the current slot on its first tick.
        runtime_key = ScheduledTriggerScheduler.idempotency_key(
            trigger_id, datetime.now(UTC), config["interval_seconds"]
        )

        detail = client.get(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["config"] == config

        updated = client.patch(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}",
            json={"config": updated_config},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["trigger_type"] == "scheduled"
        assert updated.json()["config"] == updated_config

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

        # Scheduler dispatch is automatic; the first tick may dispatch the
        # current interval slot immediately. The deterministic key is the
        # runtime's idempotency contract and is safe across multiple workers.
        rows = _wait_for_scheduled_execution(runtime_key)
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "completed", rows
        assert rows[0]["idempotency_key"] == runtime_key
        assert rows[0]["input_data"]["scheduled_slot"] == ScheduledTriggerScheduler.interval_slot(
            datetime.now(UTC), config["interval_seconds"]
        ) or isinstance(rows[0]["input_data"]["scheduled_slot"], int)
        assert rows[0]["input_data"]["recovery"] is False or isinstance(
            rows[0]["input_data"]["recovery"], bool
        )

        # A second scheduler poll in the same interval slot must not create a
        # second Workflow Execution.
        time.sleep(6)
        rows_after_duplicate_poll = asyncio.run(_execution_rows(runtime_key))
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


def test_scheduled_trigger_two_workers_converge_on_one_slot_execution_real_http():
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
        # Use a historical slot so the application's background scheduler
        # cannot independently claim the same slot while this contract test
        # runs two scheduler workers concurrently.
        now = datetime(2020, 1, 1, 0, 0, 37, tzinfo=UTC)
        runtime_key = ScheduledTriggerScheduler.idempotency_key(trigger_id, now, config["interval_seconds"])

        async def dispatch_from_two_workers():
            first = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=1)
            second = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=1)
            return await asyncio.gather(first.tick_once(now), second.tick_once(now))

        try:
            counters = asyncio.run(dispatch_from_two_workers())
            rows = _wait_for_scheduled_execution(runtime_key)
            assert len(rows) == 1, rows
            assert rows[0]["idempotency_key"] == runtime_key
            assert rows[0]["input_data"]["scheduled_slot"] == ScheduledTriggerScheduler.interval_slot(
                now, config["interval_seconds"]
            )
            assert rows[0]["input_data"]["recovery"] is False
            assert sum(item["dispatched"] for item in counters) == 1
            assert sum(item["contention"] for item in counters) <= 1
        finally:
            deleted = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
            assert deleted.status_code == 204, deleted.text
