from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_agent_routes_are_registered():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/agents")}
    assert ("/api/v1/agents", ("POST",)) in paths
    assert ("/api/v1/agents", ("GET",)) in paths
    assert ("/api/v1/agents/{agent_id}/versions", ("GET",)) in paths
    assert ("/api/v1/agents/{agent_id}/versions", ("POST",)) in paths
    assert ("/api/v1/agents/{agent_id}/published-version", ("GET",)) in paths


def test_agent_create_requires_bearer_authentication():
    response = client.post("/api/v1/agents", json={"name": "manual-test-agent"})
    assert response.status_code == 401


def test_agent_list_requires_bearer_authentication():
    response = client.get("/api/v1/agents")
    assert response.status_code == 401


def test_agent_versions_require_bearer_authentication():
    response = client.get("/api/v1/agents/00000000-0000-0000-0000-000000000001/versions")
    assert response.status_code == 401


def test_agent_version_create_requires_bearer_authentication():
    response = client.post("/api/v1/agents/00000000-0000-0000-0000-000000000001/versions", json={"system_prompt": "test", "model_id": "mock-model"})
    assert response.status_code == 401


def test_published_version_requires_bearer_authentication():
    response = client.get("/api/v1/agents/00000000-0000-0000-0000-000000000001/published-version")
    assert response.status_code == 401
