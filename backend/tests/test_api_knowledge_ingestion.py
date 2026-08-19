from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ingestion_routes_are_registered():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/knowledge")}
    assert ("/api/v1/knowledge/versions/{version_id}/ingest", ("POST",)) in paths
    assert ("/api/v1/knowledge/versions/{version_id}/chunks", ("GET",)) in paths


def test_ingestion_requires_bearer_authentication():
    version_id = "00000000-0000-0000-0000-000000000001"
    assert client.post(f"/api/v1/knowledge/versions/{version_id}/ingest").status_code == 401
    assert client.get(f"/api/v1/knowledge/versions/{version_id}/chunks").status_code == 401
