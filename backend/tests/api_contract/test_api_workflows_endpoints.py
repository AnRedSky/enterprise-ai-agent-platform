from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_workflow_routes_are_registered():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/workflows")}
    assert ("/api/v1/workflows", ("GET",)) in paths
    assert ("/api/v1/workflows", ("POST",)) in paths
    assert ("/api/v1/workflows/{workflow_id}", ("GET",)) in paths
    assert ("/api/v1/workflows/{workflow_id}", ("PATCH",)) in paths
    assert ("/api/v1/workflows/{workflow_id}", ("DELETE",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers", ("GET",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers", ("POST",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}", ("GET",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}", ("PATCH",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}", ("DELETE",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke", ("POST",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/versions", ("GET",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/versions", ("POST",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/versions/{version_id}", ("GET",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/versions/{version_id}/publish", ("POST",)) in paths


def test_workflow_create_requires_bearer_authentication():
    response = client.post("/api/v1/workflows", json={"name": "manual-test-workflow"})
    assert response.status_code == 401


def test_workflow_list_requires_bearer_authentication():
    response = client.get("/api/v1/workflows")
    assert response.status_code == 401


def test_workflow_version_create_requires_bearer_authentication():
    workflow_id = "00000000-0000-0000-0000-000000000201"
    response = client.post(f"/api/v1/workflows/{workflow_id}/versions", json={"definition": {}})
    assert response.status_code == 401


def test_workflow_publish_requires_bearer_authentication():
    workflow_id = "00000000-0000-0000-0000-000000000201"
    version_id = "00000000-0000-0000-0000-000000000202"
    response = client.post(f"/api/v1/workflows/{workflow_id}/versions/{version_id}/publish")
    assert response.status_code == 401


def test_workflow_trigger_create_requires_bearer_authentication():
    workflow_id = "00000000-0000-0000-0000-000000000201"
    response = client.post(f"/api/v1/workflows/{workflow_id}/triggers", json={"name": "manual"})
    assert response.status_code == 401


def test_workflow_trigger_invoke_requires_bearer_authentication():
    workflow_id = "00000000-0000-0000-0000-000000000201"
    trigger_id = "00000000-0000-0000-0000-000000000202"
    response = client.post(f"/api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke", json={})
    assert response.status_code == 401
