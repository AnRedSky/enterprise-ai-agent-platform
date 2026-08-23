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
from app.dependencies.db import engine as app_engine
from app.services.workflow_scheduler.runtime import ScheduledTriggerScheduler

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
TRIGGER_WORKFLOW_ID = os.getenv("TRIGGER_WORKFLOW_ID")

pytestmark = pytest.mark.real_api


@pytest.fixture(scope="module")
def scheduler_event_loop():
    """Keep one event loop alive for AsyncEngine connections used by scheduler tests.

    The real API tests are synchronous HTTP tests, but the scheduler contract calls
    the application's AsyncEngine directly. Repeated asyncio.run() calls create and
    close different loops while SQLAlchemy's AsyncEngine pool may retain a connection
    bound to the previous loop. A module-scoped loop keeps that test-owned async work
    on one lifecycle and disposes the imported application engine before the loop closes.
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        yield loop
    finally:
        loop.run_until_complete(app_engine.dispose())
        loop.close()
        asyncio.set_event_loop(None)


def _run_async(loop: asyncio.AbstractEventLoop, coroutine):
    return loop.run_until_complete(coroutine)


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


def _wait_for_scheduled_execution(
    loop: asyncio.AbstractEventLoop,
    idempotency_key: str,
    timeout_seconds: float = 15.0,
) -> list[dict]:
    deadline = time.monotonic() + timeout_seconds
    terminal_states = {"completed", "failed", "cancelled"}
    while time.monotonic() < deadline:
        rows = _run_async(loop, _execution_rows(idempotency_key))
        if rows and all(row["status"] in terminal_states for row in rows):
            return rows
        time.sleep(1.0)
    return _run_async(loop, _execution_rows(idempotency_key))


def test_scheduled_trigger_create_update_invoke_and_runtime_contract_real_http(scheduler_event_loop):
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

        runtime_key = ScheduledTriggerScheduler.idempotency_key(
            trigger_id, datetime.now(UTC), config["interval_seconds"]
        )
        runtime_slot = int(runtime_key.rsplit(":", 1)[1])

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

        rows = _wait_for_scheduled_execution(scheduler_event_loop, runtime_key)
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "completed", rows
        assert rows[0]["idempotency_key"] == runtime_key
        assert rows[0]["input_data"]["scheduled_slot"] == runtime_slot
        assert rows[0]["input_data"]["recovery"] is False

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
            # This test intentionally uses a one-slot recovery window so both workers
            # contend for exactly the same durable scheduled slot.
            assert sum(item["dispatched"] for item in counters) == 1
        finally:
            deleted = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
            assert deleted.status_code == 204, deleted.text


def test_scheduled_trigger_recovery_slot_persists_execution_metadata_real_http(scheduler_event_loop):
    if not TRIGGER_WORKFLOW_ID:
        pytest.fail("TRIGGER_WORKFLOW_ID is required for scheduled recovery validation")

    name = f"api-real-scheduled-recovery-{uuid.uuid4().hex[:8]}"
    config = {"timezone": "UTC", "interval_seconds": 60}
    trigger_id = None

    with _client() as client:
        created = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers",
            json={"name": name, "trigger_type": "scheduled", "config": config},
        )
        assert created.status_code == 201, created.text
        trigger_id = created.json()["id"]

        # Use a historical current slot so the application background scheduler
        # cannot claim the same slot while this test explicitly validates the
        # bounded recovery persistence contract.
        now = datetime(2020, 1, 1, 0, 0, 37, tzinfo=UTC)
        scheduler = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=2)
        current_slot = scheduler.interval_slot(now, config["interval_seconds"])
        recovery_slot = current_slot - 1
        recovery_key = scheduler.slot_idempotency_key(trigger_id, recovery_slot)
        current_key = scheduler.slot_idempotency_key(trigger_id, current_slot)

        try:
            counters = _run_async(scheduler_event_loop, scheduler.tick_once(now))
            recovery_rows = _wait_for_scheduled_execution(scheduler_event_loop, recovery_key)
            current_rows = _wait_for_scheduled_execution(scheduler_event_loop, current_key)

            assert counters["recovered"] >= 1, counters
            assert len(recovery_rows) == 1, recovery_rows
            assert len(current_rows) == 1, current_rows
            assert recovery_rows[0]["status"] == "completed", recovery_rows
            assert current_rows[0]["status"] == "completed", current_rows
            assert recovery_rows[0]["input_data"] == {
                "scheduled_slot": recovery_slot,
                "recovery": True,
            }
            assert current_rows[0]["input_data"] == {
                "scheduled_slot": current_slot,
                "recovery": False,
            }

            restarted = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=2)
            second_counters = _run_async(scheduler_event_loop, restarted.tick_once(now))
            assert second_counters["dispatched"] == 0, second_counters
            assert len(_run_async(scheduler_event_loop, _execution_rows(recovery_key))) == 1
            assert len(_run_async(scheduler_event_loop, _execution_rows(current_key))) == 1
        finally:
            deleted = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
            assert deleted.status_code == 204, deleted.text
