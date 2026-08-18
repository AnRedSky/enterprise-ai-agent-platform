from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_runtime_routes_are_registered():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/runtime")}
    assert ("/api/v1/runtime/executions", ("GET",)) in paths
    assert ("/api/v1/runtime/executions/{execution_id}", ("GET",)) in paths
    assert ("/api/v1/runtime/executions/{execution_id}/events", ("GET",)) in paths
    assert ("/api/v1/runtime/audit-logs", ("GET",)) in paths


def test_runtime_list_requires_bearer_authentication():
    response = client.get("/api/v1/runtime/executions")
    assert response.status_code == 401


def test_runtime_detail_requires_bearer_authentication():
    response = client.get("/api/v1/runtime/executions/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 401


def test_runtime_events_requires_bearer_authentication():
    response = client.get("/api/v1/runtime/executions/00000000-0000-0000-0000-000000000001/events")
    assert response.status_code == 401


def test_runtime_audit_logs_require_bearer_authentication():
    response = client.get("/api/v1/runtime/audit-logs")
    assert response.status_code == 401
