from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_runtime_routes_are_registered():
    paths={(route.path,tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/runtime")}
    assert ("/api/v1/runtime/executions",("GET",)) in paths
    assert ("/api/v1/runtime/executions/{execution_id}",("GET",)) in paths
    assert ("/api/v1/runtime/executions/{execution_id}/events",("GET",)) in paths
    assert ("/api/v1/runtime/audit-logs",("GET",)) in paths

def test_runtime_routes_require_bearer_authentication():
    assert client.get("/api/v1/runtime/executions").status_code==401
    assert client.get("/api/v1/runtime/executions/00000000-0000-0000-0000-000000000001").status_code==401
    assert client.get("/api/v1/runtime/executions/00000000-0000-0000-0000-000000000001/events").status_code==401
    assert client.get("/api/v1/runtime/audit-logs").status_code==401
