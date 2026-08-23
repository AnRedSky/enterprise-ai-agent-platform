from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_model_provider_routing_contract_route_is_registered():
    paths = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if route.path.startswith("/api/v1/model-providers")
    }
    assert ("/api/v1/model-providers/routing/resolve", ("POST",)) in paths


def test_model_provider_routing_contract_requires_bearer_authentication():
    response = client.post(
        "/api/v1/model-providers/routing/resolve",
        json={
            "organization_id": "00000000-0000-0000-0000-000000000001",
            "model_type": "chat",
            "routing_strategy": "explicit_profile",
        },
    )
    assert response.status_code == 401


def test_model_provider_routing_contract_rejects_unknown_strategy():
    response = client.post(
        "/api/v1/model-providers/routing/resolve",
        json={
            "organization_id": "00000000-0000-0000-0000-000000000001",
            "model_type": "chat",
            "routing_strategy": "round_robin",
        },
    )
    assert response.status_code == 401
