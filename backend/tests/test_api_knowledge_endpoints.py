from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_knowledge_routes_are_registered():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/knowledge")}
    assert ("/api/v1/knowledge", ("GET",)) in paths
    assert ("/api/v1/knowledge", ("POST",)) in paths
    assert ("/api/v1/knowledge/{knowledge_base_id}", ("GET",)) in paths
    assert ("/api/v1/knowledge/{knowledge_base_id}", ("PATCH",)) in paths
    assert ("/api/v1/knowledge/{knowledge_base_id}", ("DELETE",)) in paths
    assert ("/api/v1/knowledge/{knowledge_base_id}/documents", ("GET",)) in paths
    assert ("/api/v1/knowledge/{knowledge_base_id}/documents", ("POST",)) in paths
    assert ("/api/v1/knowledge/{knowledge_base_id}/documents/{document_id}", ("GET",)) in paths
    assert ("/api/v1/knowledge/{knowledge_base_id}/documents/{document_id}/versions", ("GET",)) in paths
    assert ("/api/v1/knowledge/{knowledge_base_id}/documents/{document_id}/versions", ("POST",)) in paths


def test_knowledge_list_requires_bearer_authentication():
    response = client.get("/api/v1/knowledge")
    assert response.status_code == 401


def test_knowledge_create_requires_bearer_authentication():
    response = client.post("/api/v1/knowledge", json={"name": "manual-test-knowledge"})
    assert response.status_code == 401


def test_knowledge_detail_requires_bearer_authentication():
    response = client.get("/api/v1/knowledge/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 401


def test_document_list_requires_bearer_authentication():
    response = client.get("/api/v1/knowledge/00000000-0000-0000-0000-000000000001/documents")
    assert response.status_code == 401


def test_document_create_requires_bearer_authentication():
    response = client.post(
        "/api/v1/knowledge/00000000-0000-0000-0000-000000000001/documents",
        json={"title": "manual-test-document"},
    )
    assert response.status_code == 401


def test_document_versions_require_bearer_authentication():
    path = "/api/v1/knowledge/00000000-0000-0000-0000-000000000001/documents/00000000-0000-0000-0000-000000000002/versions"
    assert client.get(path).status_code == 401
    assert client.post(path, json={"version": "v1"}).status_code == 401
