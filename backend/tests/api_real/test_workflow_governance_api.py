import os

import pytest
import httpx


BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")
EXECUTION_ID = os.getenv("WORKFLOW_EXECUTION_ID")


pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20.0,
    )


def test_unauthenticated_workflow_api_is_rejected():
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        response = client.get("/workflows")
    assert response.status_code == 401


def test_workflow_list_real_http_call():
    with _client() as client:
        response = client.get("/workflows")
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_workflow_detail_and_versions_real_http_calls():
    if not WORKFLOW_ID:
        pytest.fail("WORKFLOW_ID is required for workflow detail validation")
    with _client() as client:
        workflow = client.get(f"/workflows/{WORKFLOW_ID}")
        versions = client.get(f"/workflows/{WORKFLOW_ID}/versions")
    assert workflow.status_code == 200, workflow.text
    assert versions.status_code == 200, versions.text
    assert isinstance(versions.json(), list)


def test_audit_real_http_call():
    if not WORKFLOW_ID:
        pytest.fail("WORKFLOW_ID is required for audit validation")
    with _client() as client:
        response = client.get("/runtime/audit-logs", params={"workflow_id": WORKFLOW_ID})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload.get("items"), list)
    assert isinstance(payload.get("total"), int)


def test_trace_real_http_call():
    if not EXECUTION_ID:
        pytest.skip("WORKFLOW_EXECUTION_ID not provided; trace validation skipped")
    with _client() as client:
        response = client.get(f"/runtime/executions/{EXECUTION_ID}/trace")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("execution_id") == EXECUTION_ID
    assert isinstance(payload.get("items"), list)
