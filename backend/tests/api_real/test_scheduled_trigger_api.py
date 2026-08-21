from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import UTC, datetime

import httpx
import pytest

from app.services.scheduled_trigger_scheduler import ScheduledTriggerScheduler

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
CONTEXT_PATH = os.getenv("REAL_API_CONTEXT_PATH", ".real_api_context")


def _load_context() -> dict[str, str]:
    values: dict[str, str] = {}
    if not os.path.exists(CONTEXT_PATH):
        return values
    with open(CONTEXT_PATH, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value
    return values


_CONTEXT = _load_context()
ACCESS_TOKEN = _CONTEXT.get("ACCESS_TOKEN")
TRIGGER_WORKFLOW_ID = _CONTEXT.get("TRIGGER_WORKFLOW_ID") or _CONTEXT.get("WORKFLOW_ID")


def _client() -> httpx.Client:
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"} if ACCESS_TOKEN else {}
    return httpx.Client(base_url=BASE_URL, headers=headers, timeout=10.0)


def _run_async(loop, awaitable):
    return loop.run_until_complete(awaitable)


def _wait_for_scheduled_execution(loop, runtime_key: str) -> list[dict]:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with _client() as client:
            response = client.get("/runtime/executions", params={"page": 1, "page_size": 100})
            assert response.status_code == 200, response.text
            rows = [row for row in response.json().get("items", []) if row.get("idempotency_key") == runtime_key]
            if rows:
                return rows
        loop.run_until_complete(asyncio.sleep(0.2))
    return []


def test_scheduled_trigger_crud_real_http():
    if not TRIGGER_WORKFLOW_ID:
        pytest.fail("TRIGGER_WORKFLOW_ID is required for scheduled trigger validation")

    name = f"api-real-scheduled-{uuid.uuid4().hex[:8]}"
    config = {"timezone": "UTC", "interval_seconds": 60}
    trigger_id = None

    with _client() as client:
        created = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers",
            json={"name": name, "trigger_type": "scheduled", "config": config},
        )
        assert created.status_code == 201, created.text
        payload = created.json()
        trigger_id = payload["id"]
        assert payload["status"] == "enabled"
        assert payload["trigger_type"] == "scheduled"
        assert payload["config"]["timezone"] == "UTC"
        assert payload["config"]["interval_seconds"] == 60

        listed = client.get(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers")
        assert listed.status_code == 200, listed.text
        assert any(item["id"] == trigger_id for item in listed.json())

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
            # Both workers must converge at the transaction boundary: exactly
            # one worker creates the durable slot execution and the other skips.
            assert sum(item["dispatched"] for item in counters) == 1
            assert sum(item["skipped"] for item in counters) >= 1
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
        now = datetime(2020, 1, 1, 0, 0, 37, tzinfo=UTC)
        recovery_slot = ScheduledTriggerScheduler.interval_slot(now, config["interval_seconds"]) - 1
        runtime_key = ScheduledTriggerScheduler.slot_idempotency_key(trigger_id, recovery_slot)

        async def dispatch_recovery():
            scheduler = ScheduledTriggerScheduler(poll_interval_seconds=5, recovery_slots=2)
            return await scheduler.tick_once(now)

        try:
            counters = _run_async(scheduler_event_loop, dispatch_recovery())
            rows = _wait_for_scheduled_execution(scheduler_event_loop, runtime_key)
            assert len(rows) == 1, rows
            assert rows[0]["idempotency_key"] == runtime_key
            assert rows[0]["input_data"]["scheduled_slot"] == recovery_slot
            assert rows[0]["input_data"]["recovery"] is True
            assert sum(item["recovered"] for item in [counters]) >= 1
        finally:
            deleted = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
            assert deleted.status_code == 204, deleted.text
