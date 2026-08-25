import os
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import httpx

from .execution_helpers import run_or_observe_execution

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")
EXECUTION_ID = os.getenv("WORKFLOW_EXECUTION_ID")
TRIGGER_WORKFLOW_ID = os.getenv("TRIGGER_WORKFLOW_ID")
TRIGGER_ID = os.getenv("TRIGGER_ID")
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


def _effective_run_status(run_status, persisted_execution):
    """将 Worker 抢占导致的 409 映射为业务结果，而不是把竞态误判为断言失败。

    Args:
        run_status: 真实 HTTP `/run` 返回状态码。
        persisted_execution: Worker 完成后通过真实 HTTP 查询得到的 Execution。

    Returns:
        与手动 `/run` 直接执行时等价的业务 HTTP 状态码。

    Raises:
        AssertionError: Worker 持久化结果不能对应当前 Circuit Breaker Fixture Contract。
    """
    if run_status != 409:
        return run_status
    if persisted_execution["status"] == "completed":
        return 200
    if persisted_execution["status"] == "failed" and persisted_execution.get("error_code") == "CIRCUIT_OPEN":
        return 503
    raise AssertionError(f"Worker claim race persisted unexpected execution: {persisted_execution}")


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


def test_workflow_trigger_real_http_contract():
    if not TRIGGER_WORKFLOW_ID or not TRIGGER_ID:
        pytest.fail("Trigger fixture context is required")
    with _client() as client:
        listing = client.get(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers")
        detail = client.get(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{TRIGGER_ID}")
    assert listing.status_code == 200, listing.text
    assert detail.status_code == 200, detail.text
    assert any(item["id"] == TRIGGER_ID and item["status"] == "enabled" for item in listing.json())
    trigger = detail.json()
    assert trigger["id"] == TRIGGER_ID
    assert trigger["workflow_id"] == TRIGGER_WORKFLOW_ID
    assert trigger["tenant_id"] is not None
    assert trigger["trigger_type"] == "manual"


def test_workflow_trigger_invoke_is_idempotent_and_audited():
    if not TRIGGER_WORKFLOW_ID or not TRIGGER_ID:
        pytest.fail("Trigger fixture context is required")
    key = f"real-trigger-idempotency-{os.urandom(6).hex()}"
    with _client() as client:
        first = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{TRIGGER_ID}/invoke",
            headers={"Idempotency-Key": key},
            json={"input_data": {"source": "trigger-real-api"}},
        )
        assert first.status_code == 200, first.text
        first_payload = first.json()
        second = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{TRIGGER_ID}/invoke",
            headers={"Idempotency-Key": key},
            json={"input_data": {"source": "trigger-real-api-repeated"}},
        )
        assert second.status_code == 200, second.text
        second_payload = second.json()
        nodes, trace_items, audit_items = _get_governance(client, first_payload["id"], TRIGGER_WORKFLOW_ID)
    assert second_payload["id"] == first_payload["id"]
    assert first_payload["workflow_id"] == TRIGGER_WORKFLOW_ID
    assert first_payload["status"] == "completed"
    assert nodes
    trigger_events = [item for item in trace_items if item["event_type"] == "trigger.invoked"]
    assert trigger_events and trigger_events[0]["data"]["trigger_id"] == TRIGGER_ID
    trigger_audits = [item for item in audit_items if item["action"] == "workflow.trigger.invoked"]
    assert trigger_audits and trigger_audits[0]["metadata_json"]["trigger_id"] == TRIGGER_ID


def test_workflow_trigger_disabled_fast_fails():
    if not TRIGGER_WORKFLOW_ID or not TRIGGER_ID:
        pytest.fail("Trigger fixture context is required")
    with _client() as client:
        updated = client.patch(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{TRIGGER_ID}",
            json={"status": "disabled"},
        )
        assert updated.status_code == 200, updated.text
        response = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{TRIGGER_ID}/invoke",
            json={"input_data": {"source": "disabled-trigger"}},
        )
        assert response.status_code == 409, response.text
        assert "禁用" in response.text


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
    actions = [item["action"] for item in audit_items]
    assert "workflow.node.retry" not in actions
    failed_index = actions.index("workflow.execution.failed")
    exhausted_index = actions.index("workflow.node.retry_exhausted")
    assert failed_index < exhausted_index, "审计接口按倒序返回；Execution failed 应晚于 retry_exhausted"


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
    actions = [item["action"] for item in audit_items]
    failed_index = actions.index("workflow.execution.failed")
    exhausted_index = actions.index("workflow.node.retry_exhausted")
    assert failed_index < exhausted_index, "审计接口按倒序返回；Execution failed 应晚于 retry_exhausted"


def test_circuit_breaker_opens_and_fast_fails_real_business_boundary():
    if not CIRCUIT_OPEN_WORKFLOW_ID or not CIRCUIT_OPEN_EXECUTION_ID:
        pytest.fail("Circuit breaker fixture context is required")
    with _client() as client:
        execution = _assert_failed_execution(client, CIRCUIT_OPEN_EXECUTION_ID, "CIRCUIT_OPEN")
        nodes, trace_items, audit_items = _get_governance(client, CIRCUIT_OPEN_EXECUTION_ID, CIRCUIT_OPEN_WORKFLOW_ID)
        second = client.post(f"/workflows/{CIRCUIT_OPEN_WORKFLOW_ID}/executions", json={"input_data": {"source": "circuit-fast-fail"}})
        assert second.status_code == 201, second.text
        second_id = second.json()["id"]
        second_run_status, second_persisted = run_or_observe_execution(
            client,
            second_id,
            expected_http_status=503,
        )
        assert _effective_run_status(second_run_status, second_persisted) == 503
        second_execution = _assert_failed_execution(client, second_id, "CIRCUIT_OPEN")
        second_nodes, second_trace, _second_audit = _get_governance(client, second_id, CIRCUIT_OPEN_WORKFLOW_ID)
    assert execution["error_code"] == "CIRCUIT_OPEN"
    assert nodes[0]["attempt"] == 2
    assert nodes[0]["error_code"] == "CIRCUIT_OPEN"
    assert any(item["event_type"] == "node.retry.scheduled" for item in trace_items)
    assert any(item["action"] == "workflow.execution.failed" for item in audit_items)
    assert second_execution["error_code"] == "CIRCUIT_OPEN"
    assert second_nodes[0]["attempt"] == 1
    assert second_nodes[0]["error_code"] == "CIRCUIT_OPEN"
    assert not any(item["event_type"] == "node.retry.scheduled" for item in second_trace)


def test_circuit_breaker_half_open_probe_quota_real_business_boundary():
    if not CIRCUIT_OPEN_WORKFLOW_ID or not CIRCUIT_RECOVERY_WORKFLOW_ID:
        pytest.fail("Circuit recovery fixture context is required")
    time.sleep(10.25)

    def run_execution():
        with _client() as client:
            created = client.post(
                f"/workflows/{CIRCUIT_RECOVERY_WORKFLOW_ID}/executions",
                json={"input_data": {"source": "circuit-half-open-concurrent"}},
            )
            assert created.status_code == 201, created.text
            execution_id = created.json()["id"]
            run_status, persisted = run_or_observe_execution(
                client,
                execution_id,
                expected_http_status=(200, 503),
            )
            return execution_id, run_status, persisted

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(lambda _index: run_execution(), (1, 2))

    results = [first, second]
    effective_results = [
        (_execution_id, _effective_run_status(_run_status, _persisted), _persisted)
        for _execution_id, _run_status, _persisted in results
    ]
    assert sorted(result[1] for result in effective_results) == [200, 503]
    failed_id = next(result[0] for result in effective_results if result[1] == 503)
    successful_id = next(result[0] for result in effective_results if result[1] == 200)
    with _client() as client:
        failed = _assert_failed_execution(client, failed_id, "CIRCUIT_OPEN")
        successful = client.get(f"/workflows/executions/{successful_id}")
        failed_nodes, failed_trace, _ = _get_governance(client, failed_id, CIRCUIT_RECOVERY_WORKFLOW_ID)
    assert failed["error_code"] == "CIRCUIT_OPEN"
    assert failed_nodes[0]["attempt"] == 1
    assert failed_nodes[0]["error_code"] == "CIRCUIT_OPEN"
    assert not any(item["event_type"] == "node.retry.scheduled" for item in failed_trace)
    assert successful.status_code == 200, successful.text
    assert successful.json()["status"] == "completed"


def test_circuit_breaker_half_open_probe_recovers_and_closes():
    if not CIRCUIT_OPEN_WORKFLOW_ID or not CIRCUIT_RECOVERY_WORKFLOW_ID:
        pytest.fail("Circuit recovery fixture context is required")
    with _client() as client:
        execution = client.post(f"/workflows/{CIRCUIT_RECOVERY_WORKFLOW_ID}/executions", json={"input_data": {"source": "circuit-recovery"}})
        assert execution.status_code == 201, execution.text
        execution_id = execution.json()["id"]
        run_status, persisted = run_or_observe_execution(
            client,
            execution_id,
            expected_http_status=200,
        )
        assert _effective_run_status(run_status, persisted) == 200
        payload = persisted
        assert payload["status"] == "completed"
        nodes, trace_items, audit_items = _get_governance(client, execution_id, CIRCUIT_RECOVERY_WORKFLOW_ID)
        follow_up = client.post(f"/workflows/{CIRCUIT_RECOVERY_WORKFLOW_ID}/executions", json={"input_data": {"source": "circuit-closed"}})
        assert follow_up.status_code == 201, follow_up.text
        follow_up_id = follow_up.json()["id"]
        follow_up_run_status, follow_up_persisted = run_or_observe_execution(
            client,
            follow_up_id,
            expected_http_status=200,
        )
        assert _effective_run_status(follow_up_run_status, follow_up_persisted) == 200
    assert nodes[0]["status"] == "completed"
    assert nodes[0]["attempt"] == 1
    assert any(item["event_type"] == "node.state_changed" and item["status"] == "completed" for item in trace_items)
    assert any(item["action"] == "workflow.execution.completed" for item in audit_items)
