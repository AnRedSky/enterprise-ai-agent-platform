import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
MEMBER_TOKEN = os.getenv("ORGANIZATION_MEMBER_ACCESS_TOKEN")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")

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
        name
        for name, value in {
            "ORGANIZATION_ID": ORGANIZATION_ID,
            "ORGANIZATION_MEMBER_ACCESS_TOKEN": MEMBER_TOKEN,
        }.items()
        if not value
    ]
    if missing:
        pytest.fail(f"Model Provider real API fixture context is missing: {', '.join(missing)}")


def test_model_provider_profile_governance_lifecycle_real_http():
    _require_context()
    suffix = uuid.uuid4().hex[:10]
    provider_id = None
    profile_ids: list[str] = []

    with _client() as client:
        created = client.post(
            "/model-providers",
            headers={"X-Request-Id": f"e4-provider-{suffix}", "X-Trace-Id": f"e4-trace-{suffix}"},
            json={
                "organization_id": ORGANIZATION_ID,
                "name": f"e4-provider-{suffix}",
                "provider_type": "embedding",
                "provider_name": "governed-test-provider",
                "endpoint": "http://provider.invalid/v1",
                "credential_ref": "secret://e4/provider",
            },
        )
        assert created.status_code == 201, created.text
        provider = created.json()
        provider_id = provider["id"]
        assert provider["organization_id"] == ORGANIZATION_ID
        assert provider["credential_ref"] == "secret://e4/provider"

        chat = client.post(
            f"/model-providers/{provider_id}/profiles",
            json={
                "name": f"chat-{suffix}",
                "model_type": "chat",
                "model_name": "governed-chat-model",
                "dimension": None,
                "is_default": True,
            },
        )
        assert chat.status_code == 201, chat.text
        chat_profile = chat.json()
        profile_ids.append(chat_profile["id"])
        assert chat_profile["dimension"] is None
        assert chat_profile["is_default"] is True

        embedding = client.post(
            f"/model-providers/{provider_id}/profiles",
            json={
                "name": f"embedding-{suffix}",
                "model_type": "embedding",
                "model_name": "governed-embedding-model",
                "dimension": 768,
                "is_default": True,
            },
        )
        assert embedding.status_code == 201, embedding.text
        embedding_profile = embedding.json()
        profile_ids.append(embedding_profile["id"])
        assert embedding_profile["dimension"] == 768
        assert embedding_profile["is_default"] is True

        profiles = client.get(f"/model-providers/{provider_id}/profiles")
        assert profiles.status_code == 200, profiles.text
        listed = profiles.json()
        assert {item["id"] for item in listed} >= set(profile_ids)
        assert sum(item["model_type"] == "chat" and item["is_default"] for item in listed) == 1
        assert sum(item["model_type"] == "embedding" and item["is_default"] for item in listed) == 1

        invalid_chat = client.post(
            f"/model-providers/{provider_id}/profiles",
            json={
                "name": f"invalid-chat-{suffix}",
                "model_type": "chat",
                "model_name": "invalid-chat-model",
                "dimension": 768,
            },
        )
        assert invalid_chat.status_code == 422, invalid_chat.text

        invalid_embedding = client.post(
            f"/model-providers/{provider_id}/profiles",
            json={
                "name": f"invalid-embedding-{suffix}",
                "model_type": "embedding",
                "model_name": "invalid-embedding-model",
            },
        )
        assert invalid_embedding.status_code == 422, invalid_embedding.text

        updated = client.patch(
            f"/model-providers/model-profiles/{embedding_profile['id']}",
            json={"model_name": "governed-embedding-model-updated", "is_default": True},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["model_name"] == "governed-embedding-model-updated"

        audit = client.get("/runtime/audit-logs")
        assert audit.status_code == 200, audit.text
        actions = [item["action"] for item in audit.json().get("items", [])]
        assert "model_provider.created" in actions
        assert "model_profile.created" in actions
        assert "model_profile.updated" in actions

        # The shared real-API bootstrap fixture currently provisions the secondary
        # organization membership as admin because organization governance tests
        # later exercise owner transfer. This provider boundary test must establish
        # its own member state before asserting management denial.
        demoted = client.patch(
            f"/organizations/{ORGANIZATION_ID}/members/{os.getenv('ORGANIZATION_MEMBERSHIP_ID')}",
            json={"role": "member"},
        )
        assert demoted.status_code == 200, demoted.text
        assert demoted.json()["role"] == "member"

    with _client(MEMBER_TOKEN) as member_client:
        forbidden_provider = member_client.patch(
            f"/model-providers/{provider_id}",
            json={"enabled": False},
        )
        assert forbidden_provider.status_code == 403, forbidden_provider.text

        forbidden_profile = member_client.patch(
            f"/model-providers/model-profiles/{profile_ids[0]}",
            json={"enabled": False},
        )
        assert forbidden_profile.status_code == 403, forbidden_profile.text

    with _client() as client:
        for profile_id in profile_ids:
            deleted = client.delete(f"/model-providers/model-profiles/{profile_id}")
            assert deleted.status_code == 204, deleted.text
        deleted_provider = client.delete(f"/model-providers/{provider_id}")
        assert deleted_provider.status_code == 204, deleted_provider.text
