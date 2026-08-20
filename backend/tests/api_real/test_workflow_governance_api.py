import os

import pytest
import httpx


BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")
EXECUTION_ID = os.getenv("WORKFLOW_EXECUTION_ID")
RETRY_WORKFLOW_ID = os.getenv("RETRY_WORKFLOW_ID")
RETRY_EXECUTION_ID = os.getenv("RETRY_EXECUTION_ID")


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


def test_node_retry_real_business_loop():
    if not RETRY_WORKFLOW_ID or not RETRY_EXECUTION_ID:
        pytest.fail("Retry fixture context is required for node retry governance validation")

    with _client() as client:
        execution = client.get(f"/workflows/executions/{RETRY_EXECUTION_ID}")
        nodes = client.get(f"/workflows/executions/{RETRY_EXECUTION_ID}/nodes")
        trace = client.get(f"/workflows/executions/{RETRY_EXECUTION_ID}/trace")
        audit = client.get(
            "/runtime/audit-logs",
            params={"workflow_execution_id": RETRY_EXECUTION_ID, "workflow_id": RETRY_WORKFLOW_ID},
        )

    assert execution.status_code == 200, execution.text
    execution_payload = execution.json()
    assert execution_payload["status"] == "failed"
    assert execution_payload["error_code"] == "HTTP_404"

    assert nodes.status_code == 200, nodes.text
    node_items = nodes.json()
    assert len(node_items) == 1
    node = node_items[0]
    assert node["node_id"] == "retry-agent"
    assert node["status"] == "failed"
    assert node["attempt"] == 2
    assert node["error_code"] == "HTTP_404"

    assert trace.status_code == 200, trace.text
    trace_items = trace.json()
    assert any(item["event_type"] == "node.retry.scheduled" and item["status"] == "retrying" for item in trace_items)
    retry_state_events = [
        item for item in trace_items
        if item["event_type"] == "node.state_changed" and item["node_id"] == "retry-agent"
    ]
    assert any((item.get("data") or {}).get("attempt") == 1 for item in retry_state_events)
    assert any((item.get("data") or {}).get("attempt") == 2 for item in retry_state_events)
    assert any(item["event_type"] == "execution.state_changed" and item["status"] == "failed" for item in trace_items)

    assert audit.status_code == 200, audit.text
    audit_items = audit.json()["items"]
    assert any(item["action"] == "workflow.node.retry" and item["status"] == "retrying" for item in audit_items)
    assert any(item["action"] == "workflow.execution.failed" and item["status"] == "failed" for item in audit_items)
