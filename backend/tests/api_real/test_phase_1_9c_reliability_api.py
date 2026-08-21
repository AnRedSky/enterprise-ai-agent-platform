import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")

pytestmark = pytest.mark.real_api


def _client(token: str | None = None) -> httpx.Client:
    token = token or TOKEN
    if not token:
        pytest.fail("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20.0,
    )


def _create_execution(key: str) -> tuple[int, dict]:
    with _client() as client:
        response = client.post(
            f"/workflows/{WORKFLOW_ID}/executions",
            headers={"Idempotency-Key": key},
            json={"input_data": {"source": "phase-1-9-c-idempotency"}},
        )
        return response.status_code, response.json()


def test_execution_idempotency_replays_same_execution():
    if not WORKFLOW_ID:
        pytest.fail("WORKFLOW_ID is required for 1.9-C reliability validation")

    key = f"phase-1-9-c-idempotency-{uuid.uuid4().hex}"
    first_status, first = _create_execution(key)
    second_status, second = _create_execution(key)

    assert first_status == 201, first
    assert second_status == 201, second
    assert second["id"] == first["id"]
    assert second["workflow_id"] == first["workflow_id"]
    assert second["idempotency_key"] == key
    assert second["status"] == "pending"


def test_execution_idempotency_is_race_safe_over_real_http():
    if not WORKFLOW_ID:
        pytest.fail("WORKFLOW_ID is required for 1.9-C reliability validation")

    key = f"phase-1-9-c-race-{uuid.uuid4().hex}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: _create_execution(key), (1, 2)))

    statuses = [status for status, _payload in results]
    payloads = [payload for _status, payload in results]
    assert statuses == [201, 201] or statuses == [201, 201], statuses
    ids = {payload["id"] for payload in payloads}
    assert len(ids) == 1, payloads
    assert all(payload["idempotency_key"] == key for payload in payloads)


def test_execution_access_isolation_blocks_another_user():
    if not WORKFLOW_ID:
        pytest.fail("WORKFLOW_ID is required for 1.9-C reliability validation")

    password = f"Phase1.9C!{uuid.uuid4().hex[:16]}"
    username = f"phase_1_9_c_{uuid.uuid4().hex[:12]}"
    with _client() as client:
        registration = client.post(
            "/auth/register",
            json={"username": username, "password": password},
        )
        assert registration.status_code == 200, registration.text
        login = client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        assert login.status_code == 200, login.text
        other_token = login.json()["access_token"]

        created = client.post(
            f"/workflows/{WORKFLOW_ID}/executions",
            json={"input_data": {"source": "phase-1-9-c-access-isolation"}},
        )
        assert created.status_code == 201, created.text
        execution_id = created.json()["id"]

    with _client(other_token) as other_client:
        response = other_client.get(f"/workflows/executions/{execution_id}")

    assert response.status_code == 404, response.text
