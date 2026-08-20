import os

import pytest
import httpx

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")
EXECUTION_ID = os.getenv("WORKFLOW_EXECUTION_ID")
RETRY_WORKFLOW_ID = os.getenv("RETRY_WORKFLOW_ID")
RETRY_EXECUTION_ID = os.getenv("RETRY_EXECUTION_ID")
RETRY_BUDGET_WORKFLOW_ID = os.getenv("RETRY_BUDGET_WORKFLOW_ID")
RETRY_BUDGET_EXECUTION_ID = os.getenv("RETRY_BUDGET_EXECUTION_ID")
RETRY_DEADLINE_WORKFLOW_ID = os.getenv("RETRY_DEADLINE_WORKFLOW_ID")
RETRY_DEADLINE_EXECUTION_ID = os.getenv("RETRY_DEADLINE_EXECUTION_ID")
CIRCUIT_OPEN_WORKFLOW_ID = os.getenv("CIRCUIT_OPEN_WORKFLOW_ID")
CIRCUIT_OPEN_EXECUTION_ID = os.getenv("CIRCUIT_OPEN_EXECUTION_ID")
CIRCUIT_RECOVERY_WORKFLOW_ID = os.getenv("CIRCUIT_RECOVERY_WORKFLOW_ID")

pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=20.0)


def _assert_failed_execution(client, execution_id, error_code):
    response = client.get(f"/workflows/executions/{execution_id}")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["error_code"] == error_code
    return payload


def _get_governance(client, execution_id, workflow_id):
    nodes = client.get(f"/workflows/executions/{execution_id}/nodes")
    trace = client.get(f"/workflows/executions/{execution_id}/trace")
    audit = client.get("/runtime/audit-logs", params={"workflow_execution_id": execution_id, "workflow_id": workflow_id})
    assert nodes.status_code == 200, nodes.text
    assert trace.status_code == 200, trace.text
    assert audit.status_code == 200, audit.text
    return nodes.json(), trace.json(), audit.json()["items"]


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
        nodes, trace_items, audit_items = _get_governance(client, RETRY_EXECUTION_ID, RETRY_WORKFLOW_ID)
    assert execution.status_code == 200, execution.text
    payload = execution.json()
    assert payload["status"] == "failed"
    assert payload["error_code"] == "HTTP_404"
    assert len(nodes) == 1 and nodes[0]["attempt"] == 2 and nodes[0]["error_code"] == "HTTP_404"
    trace_types = [item["event_type"] for item in trace_items]
    scheduled_index = trace_types.index("node.retry.scheduled")
    failed_indexes = [i for i, item in enumerate(trace_items) if item["event_type"] == "node.state_changed" and item["node_id"] == "retry-agent" and item["status"] == "failed"]
    assert len(failed_indexes) == 2
    assert failed_indexes[0] < scheduled_index < failed_indexes[1]
    final_execution_index = max(i for i, item in enumerate(trace_items) if item["event_type"] == "execution.state_changed" and item["status"] == "failed")
    assert failed_indexes[-1] < final_execution_index
    audit_actions = [item["action"] for item in audit_items]
    assert {"workflow.node.retry", "workflow.node.retry_exhausted", "workflow.execution.failed"}.issubset(audit_actions)


def test_retry_budget_exhausted_real_business_boundary():
    if not RETRY_BUDGET_WORKFLOW_ID or not RETRY_BUDGET_EXECUTION_ID:
        pytest.fail("Retry budget fixture context is required")
    with _client() as client:
        execution = _assert_failed_execution(client, RETRY_BUDGET_EXECUTION_ID, "HTTP_404")
        nodes, trace_items, audit_items = _get_governance(client, RETRY_BUDGET_EXECUTION_ID, RETRY_BUDGET_WORKFLOW_ID)
    assert nodes[0]["attempt"] == 1
    assert nodes[0]["error_code"] == "HTTP_404"
    assert not any(item["event_type"] == "node.retry.scheduled" for item in trace_items)
    exhausted = [item for item in trace_items if item["event_type"] == "node.retry.exhausted"]
    assert exhausted and exhausted[-1]["data"]["reason"] == "retry_budget"
    actions = [item["action"] for item in reversed(audit_items)]
    assert "workflow.node.retry" not in actions
    assert actions.index("workflow.node.retry_exhausted") < actions.index("workflow.execution.failed")


def test_retry_workflow_deadline_real_business_boundary():
    if not RETRY_DEADLINE_WORKFLOW_ID or not RETRY_DEADLINE_EXECUTION_ID:
        pytest.fail("Retry deadline fixture context is required")
    with _client() as client:
        execution = _assert_failed_execution(client, RETRY_DEADLINE_EXECUTION_ID, "WORKFLOW_TIMEOUT")
        nodes, trace_items, audit_items = _get_governance(client, RETRY_DEADLINE_EXECUTION_ID, RETRY_DEADLINE_WORKFLOW_ID)
    assert nodes[0]["attempt"] == 1
    assert nodes[0]["error_code"] == "HTTP_404"
    scheduled = [item for item in trace_items if item["event_type"] == "node.retry.scheduled"]
    assert not scheduled, "Retry must not be scheduled when its delay exceeds the workflow deadline"
    exhausted = [item for item in trace_items if item["event_type"] == "node.retry.exhausted"]
    assert exhausted and exhausted[-1]["data"]["reason"] == "workflow_deadline"
    assert exhausted[-1]["error_code"] == "WORKFLOW_TIMEOUT"
    execution_failed = [item for item in trace_items if item["event_type"] == "execution.state_changed" and item["status"] == "failed"]
    assert execution_failed and execution_failed[-1]["error_code"] == "WORKFLOW_TIMEOUT"
    actions = [item["action"] for item in reversed(audit_items)]
    assert actions.index("workflow.node.retry_exhausted") < actions.index("workflow.execution.failed")


def test_circuit_breaker_opens_and_fast_fails_real_business_boundary():
    if not CIRCUIT_OPEN_WORKFLOW_ID or not CIRCUIT_OPEN_EXECUTION_ID:
        pytest.fail("Circuit breaker fixture context is required")
    with _client() as client:
        execution = _assert_failed_execution(client, CIRCUIT_OPEN_EXECUTION_ID, "CIRCUIT_OPEN")
        nodes, trace_items, audit_items = _get_governance(client, CIRCUIT_OPEN_EXECUTION_ID, CIRCUIT_OPEN_WORKFLOW_ID)
        second = client.post(f"/workflows/{CIRCUIT_OPEN_WORKFLOW_ID}/executions", json={"input_data": {"source": "circuit-fast-fail"}})
        assert second.status_code == 201, second.text
        second_run = client.post(f"/workflows/executions/{second.json()['id']}/run")
        assert second_run.status_code == 503, second_run.text
        second_execution = _assert_failed_execution(client, second.json()["id"], "CIRCUIT_OPEN")
        second_nodes, second_trace, _second_audit = _get_governance(client, second.json()["id"], CIRCUIT_OPEN_WORKFLOW_ID)
    assert execution["error_code"] == "CIRCUIT_OPEN"
    assert nodes[0]["attempt"] == 2
    assert nodes[0]["error_code"] == "CIRCUIT_OPEN"
    assert any(item["event_type"] == "node.retry.scheduled" for item in trace_items)
    assert any(item["action"] == "workflow.execution.failed" for item in audit_items)
    assert second_execution["error_code"] == "CIRCUIT_OPEN"
    assert second_nodes[0]["attempt"] == 1
    assert second_nodes[0]["error_code"] == "CIRCUIT_OPEN"
    assert not any(item["event_type"] == "node.retry.scheduled" for item in second_trace)


def test_circuit_breaker_half_open_probe_recovers_and_closes():
    if not CIRCUIT_OPEN_WORKFLOW_ID or not CIRCUIT_RECOVERY_WORKFLOW_ID:
        pytest.fail("Circuit recovery fixture context is required")
    import time
    time.sleep(0.25)
    with _client() as client:
        execution = client.post(f"/workflows/{CIRCUIT_RECOVERY_WORKFLOW_ID}/executions", json={"input_data": {"source": "circuit-recovery"}})
        assert execution.status_code == 201, execution.text
        execution_id = execution.json()["id"]
        run = client.post(f"/workflows/executions/{execution_id}/run")
        assert run.status_code == 200, run.text
        payload = run.json()
        assert payload["status"] == "completed"
        nodes, trace_items, audit_items = _get_governance(client, execution_id, CIRCUIT_RECOVERY_WORKFLOW_ID)
        follow_up = client.post(f"/workflows/{CIRCUIT_RECOVERY_WORKFLOW_ID}/executions", json={"input_data": {"source": "circuit-closed"}})
        assert follow_up.status_code == 201, follow_up.text
        follow_up_id = follow_up.json()["id"]
        follow_up_run = client.post(f"/workflows/executions/{follow_up_id}/run")
        assert follow_up_run.status_code == 200, follow_up_run.text
    assert nodes[0]["status"] == "completed"
    assert nodes[0]["attempt"] == 1
    assert any(item["event_type"] == "node.state_changed" and item["status"] == "completed" for item in trace_items)
    assert any(item["action"] == "workflow.execution.completed" for item in audit_items)
