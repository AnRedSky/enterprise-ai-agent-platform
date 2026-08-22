from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_organization_routes_are_registered():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/organizations")}
    assert ("/api/v1/organizations", ("GET",)) in paths
    assert ("/api/v1/organizations", ("POST",)) in paths
    assert ("/api/v1/organizations/{organization_id}", ("GET",)) in paths
    assert ("/api/v1/organizations/{organization_id}", ("PATCH",)) in paths
    assert ("/api/v1/organizations/{organization_id}/members", ("GET",)) in paths
    assert ("/api/v1/organizations/{organization_id}/members", ("POST",)) in paths
    assert ("/api/v1/organizations/{organization_id}/members/{membership_id}", ("PATCH",)) in paths
    assert ("/api/v1/organizations/{organization_id}/members/{membership_id}", ("DELETE",)) in paths
    assert ("/api/v1/organizations/{organization_id}/members/{membership_id}/transfer-owner", ("POST",)) in paths


def test_organization_list_requires_bearer_authentication():
    response = client.get("/api/v1/organizations")
    assert response.status_code == 401


def test_organization_create_requires_bearer_authentication():
    response = client.post("/api/v1/organizations", json={"name": "Acme AI"})
    assert response.status_code == 401


def test_organization_member_management_requires_bearer_authentication():
    organization_id = "00000000-0000-0000-0000-000000000001"
    membership_id = "00000000-0000-0000-0000-000000000002"
    assert client.get(f"/api/v1/organizations/{organization_id}").status_code == 401
    assert client.patch(f"/api/v1/organizations/{organization_id}", json={"status": "suspended"}).status_code == 401
    assert client.get(f"/api/v1/organizations/{organization_id}/members").status_code == 401
    assert client.post(
        f"/api/v1/organizations/{organization_id}/members",
        json={"user_id": membership_id, "role": "member"},
    ).status_code == 401
    assert client.patch(
        f"/api/v1/organizations/{organization_id}/members/{membership_id}",
        json={"status": "suspended"},
    ).status_code == 401
    assert client.delete(
        f"/api/v1/organizations/{organization_id}/members/{membership_id}"
    ).status_code == 401
    assert client.post(
        f"/api/v1/organizations/{organization_id}/members/{membership_id}/transfer-owner"
    ).status_code == 401
