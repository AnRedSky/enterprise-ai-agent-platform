from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_model_usage_route_is_registered():
    paths = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if route.path.startswith("/api/v1/usage")
    }
    assert ("/api/v1/usage/model", ("GET",)) in paths


def test_model_usage_requires_bearer_authentication():
    response = client.get(
        "/api/v1/usage/model",
        params={"organization_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 401


def test_model_usage_validates_pagination_without_auth_leakage():
    response = client.get(
        "/api/v1/usage/model",
        params={
            "organization_id": "00000000-0000-0000-0000-000000000001",
            "offset": -1,
        },
    )
    assert response.status_code == 401
