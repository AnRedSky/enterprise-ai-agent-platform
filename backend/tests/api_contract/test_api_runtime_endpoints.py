from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_runtime_routes_are_registered():
    paths = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if route.path.startswith("/api/v1/runtime")
    }
    assert ("/api/v1/runtime/executions", ("GET",)) in paths
    assert ("/api/v1/runtime/executions/{execution_id}", ("GET",)) in paths
    assert ("/api/v1/runtime/executions/{execution_id}/events", ("GET",)) in paths
    assert ("/api/v1/runtime/retrieval-evaluations/{evaluation_run_id}", ("GET",)) in paths
    assert ("/api/v1/runtime/audit-logs", ("GET",)) in paths
    assert ("/api/v1/runtime/integration-events", ("GET",)) in paths
    assert ("/api/v1/runtime/integration-events/summary", ("GET",)) in paths
    assert ("/api/v1/runtime/integration-events/{integration_event_id}/deliveries", ("GET",)) in paths
    assert ("/api/v1/runtime/correlations/executions/{execution_id}", ("GET",)) in paths
    assert ("/api/v1/runtime/correlations/traces/{trace_id}", ("GET",)) in paths
    assert ("/api/v1/runtime/correlations/audits/{audit_id}", ("GET",)) in paths
    assert ("/api/v1/runtime/correlations/operator-actions/{operator_action_id}", ("GET",)) in paths


def test_runtime_routes_require_bearer_authentication():
    execution_id = "00000000-0000-0000-0000-000000000001"
    event_id = "00000000-0000-0000-0000-000000000002"
    trace_id = "trace-contract-1"
    audit_id = "00000000-0000-0000-0000-000000000003"
    operator_action_id = "00000000-0000-0000-0000-000000000004"
    assert client.get("/api/v1/runtime/executions").status_code == 401
    assert client.get(f"/api/v1/runtime/executions/{execution_id}").status_code == 401
    assert client.get(f"/api/v1/runtime/executions/{execution_id}/events").status_code == 401
    assert client.get(f"/api/v1/runtime/retrieval-evaluations/{execution_id}").status_code == 401
    assert client.get("/api/v1/runtime/audit-logs").status_code == 401
    assert client.get("/api/v1/runtime/integration-events").status_code == 401
    assert client.get("/api/v1/runtime/integration-events/summary").status_code == 401
    assert client.get(f"/api/v1/runtime/integration-events/{event_id}/deliveries").status_code == 401
    assert client.get(f"/api/v1/runtime/correlations/executions/{execution_id}").status_code == 401
    assert client.get(f"/api/v1/runtime/correlations/traces/{trace_id}").status_code == 401
    assert client.get(f"/api/v1/runtime/correlations/audits/{audit_id}").status_code == 401
    assert client.get(f"/api/v1/runtime/correlations/operator-actions/{operator_action_id}").status_code == 401
