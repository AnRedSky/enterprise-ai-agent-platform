import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
MEMBER_TOKEN = os.getenv("ORGANIZATION_MEMBER_ACCESS_TOKEN")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")
MEMBERSHIP_ID = os.getenv("ORGANIZATION_MEMBERSHIP_ID")
MEMBER_USER_ID = os.getenv("ORGANIZATION_MEMBER_USER_ID")

pytestmark = pytest.mark.real_api


def _client(token: str | None = None) -> httpx.Client:
    token = token or TOKEN
    if not token:
        pytest.fail("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20.0,
    )


def _require_context() -> None:
    missing = [
        name for name, value in {
            "ORGANIZATION_ID": ORGANIZATION_ID,
            "ORGANIZATION_MEMBERSHIP_ID": MEMBERSHIP_ID,
            "ORGANIZATION_MEMBER_USER_ID": MEMBER_USER_ID,
            "ORGANIZATION_MEMBER_ACCESS_TOKEN": MEMBER_TOKEN,
        }.items() if not value
    ]
    if missing:
        pytest.fail(f"Organization real API fixture context is missing: {', '.join(missing)}")


def test_organization_list_real_http_contract():
    _require_context()
    with _client() as client:
        response = client.get("/organizations")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload.get("items"), list)
    assert any(item["id"] == ORGANIZATION_ID and item["status"] == "active" for item in payload["items"])


def test_organization_detail_and_membership_real_http_contract():
    _require_context()
    with _client() as client:
        organization = client.get(f"/organizations/{ORGANIZATION_ID}")
        members = client.get(f"/organizations/{ORGANIZATION_ID}/members")
    assert organization.status_code == 200, organization.text
    assert members.status_code == 200, members.text
    assert organization.json()["id"] == ORGANIZATION_ID
    items = members.json()["items"]
    assert any(item["id"] == MEMBERSHIP_ID and item["user_id"] == MEMBER_USER_ID for item in items)


def test_membership_role_and_status_lifecycle_real_http():
    _require_context()
    with _client() as client:
        updated_role = client.patch(
            f"/organizations/{ORGANIZATION_ID}/members/{MEMBERSHIP_ID}",
            json={"role": "member"},
        )
        assert updated_role.status_code == 200, updated_role.text
        assert updated_role.json()["role"] == "member"

        suspended = client.patch(
            f"/organizations/{ORGANIZATION_ID}/members/{MEMBERSHIP_ID}",
            json={"status": "suspended"},
        )
        assert suspended.status_code == 200, suspended.text
        assert suspended.json()["status"] == "suspended"

    with _client(MEMBER_TOKEN) as member_client:
        blocked = member_client.get(f"/organizations/{ORGANIZATION_ID}")
    assert blocked.status_code == 403, blocked.text

    with _client() as client:
        restored = client.patch(
            f"/organizations/{ORGANIZATION_ID}/members/{MEMBERSHIP_ID}",
            json={"status": "active"},
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["status"] == "active"


def test_member_cannot_manage_or_transfer_owner_real_http():
    _require_context()
    with _client(MEMBER_TOKEN) as member_client:
        management = member_client.patch(
            f"/organizations/{ORGANIZATION_ID}",
            json={"name": "forbidden organization mutation"},
        )
        assert management.status_code == 403, management.text

        transfer = member_client.post(
            f"/organizations/{ORGANIZATION_ID}/members/{MEMBERSHIP_ID}/transfer-owner"
        )
        assert transfer.status_code == 403, transfer.text


def test_owner_transfer_is_explicit_and_preserves_single_owner():
    _require_context()
    with _client() as client:
        transferred = client.post(
            f"/organizations/{ORGANIZATION_ID}/members/{MEMBERSHIP_ID}/transfer-owner"
        )
        assert transferred.status_code == 200, transferred.text
        assert transferred.json()["id"] == MEMBERSHIP_ID
        assert transferred.json()["role"] == "owner"

        members = client.get(f"/organizations/{ORGANIZATION_ID}/members")
        assert members.status_code == 200, members.text
        owners = [item for item in members.json()["items"] if item["role"] == "owner" and item["status"] == "active"]
        assert len(owners) == 1
        assert owners[0]["id"] == MEMBERSHIP_ID


def test_transferred_owner_can_manage_and_previous_owner_cannot_manage_current_owner():
    _require_context()
    updated_name = f"API Real Organization Updated {uuid.uuid4().hex[:8]}"
    with _client(MEMBER_TOKEN) as new_owner_client:
        updated = new_owner_client.patch(
            f"/organizations/{ORGANIZATION_ID}",
            json={"name": updated_name},
        )
        assert updated.status_code == 200, updated.text

    with _client() as previous_owner_client:
        removed = previous_owner_client.delete(
            f"/organizations/{ORGANIZATION_ID}/members/{MEMBERSHIP_ID}"
        )
        assert removed.status_code == 403, removed.text


def test_organization_audit_is_written_for_management_mutations():
    _require_context()
    with _client(MEMBER_TOKEN) as client:
        response = client.get("/runtime/audit-logs")
    assert response.status_code == 200, response.text
    actions = [item["action"] for item in response.json().get("items", [])]
    assert "organization.updated" in actions
