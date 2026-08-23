from __future__ import annotations

import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")

pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20.0,
    )


def _require_context() -> None:
    if not ORGANIZATION_ID:
        pytest.fail("ORGANIZATION_ID is required for runtime governance validation")


def test_runtime_uses_published_model_profile_and_never_falls_back_to_mock():
    _require_context()
    suffix = uuid.uuid4().hex[:10]
    provider_ids: list[str] = []
    profile_ids: list[str] = []
    agent_id = None
    workflow_id = None

    with _client() as client:
        provider = client.post(
            "/model-providers",
            json={
                "organization_id": ORGANIZATION_ID,
                "name": f"runtime-governed-{suffix}",
                "provider_type": "openai-compatible",
                "provider_name": "runtime-governed-invalid-endpoint",
                "endpoint": "http://127.0.0.1:1/v1",
                "credential_ref": "RUNTIME_GOVERNANCE_TEST_SECRET",
            },
        )
        assert provider.status_code == 201, provider.text
        provider_id = provider.json()["id"]
        provider_ids.append(provider_id)

        profile = client.post(
            f"/model-providers/{provider_id}/profiles",
            json={
                "name": f"runtime-chat-{suffix}",
                "model_type": "chat",
                "model_name": f"runtime-governed-model-{suffix}",
                "is_default": True,
            },
        )
        assert profile.status_code == 201, profile.text
        profile_id = profile.json()["id"]
        profile_ids.append(profile_id)

        agent = client.post(
            "/agents",
            json={
                "name": f"Runtime Governed Agent {suffix}",
                "description": "Phase 2.3 runtime governance real API fixture",
                "system_prompt": "You are a deterministic runtime governance validation agent.",
                "model_id": f"legacy-model-{suffix}",
                "model_profile_id": profile_id,
            },
        )
        assert agent.status_code == 200, agent.text
        agent_id = agent.json()["id"]
        assert agent.json()["model_profile_id"] == profile_id

        published = client.post(
            f"/agents/{agent_id}/publish",
            json={"version_id": agent.json()["published_version_id"]},
        )
        assert published.status_code == 200, published.text
        assert published.json()["model_profile_id"] == profile_id

        workflow = client.post(
            "/workflows",
            json={
                "name": f"Runtime Governance {suffix}",
                "description": "Phase 2.3 runtime governance real API fixture",
            },
        )
        assert workflow.status_code == 201, workflow.text
        workflow_id = workflow.json()["id"]

        version = client.post(
            f"/workflows/{workflow_id}/versions",
            json={
                "definition": {
                    "config": {"timeout_ms": 5000},
                    "nodes": [
                        {
                            "id": "governed-agent",
                            "type": "agent",
                            "config": {
                                "agent_id": agent_id,
                                "prompt": "runtime governance failure semantics",
                                "retry": {
                                    "max_attempts": 1,
                                    "backoff_ms": 0,
                                    "max_backoff_ms": 0,
                                    "jitter_ms": 0,
                                    "retryable_error_codes": [],
                                },
                            },
                        }
                    ],
                    "edges": [],
                }
            },
        )
        assert version.status_code == 201, version.text
        version_id = version.json()["id"]

        publish = client.post(f"/workflows/{workflow_id}/versions/{version_id}/publish")
        assert publish.status_code == 200, publish.text

        execution = client.post(
            f"/workflows/{workflow_id}/executions",
            json={"input_data": {"source": "phase-2.3-runtime-governance"}},
        )
        assert execution.status_code == 201, execution.text
        execution_id = execution.json()["id"]

        run = client.post(f"/workflows/executions/{execution_id}/run")
        assert run.status_code == 500, run.text

        persisted = client.get(f"/workflows/executions/{execution_id}")
        assert persisted.status_code == 200, persisted.text
        payload = persisted.json()
        assert payload["status"] == "failed"
        assert payload["error_code"] == "ConnectError"

        trace = client.get(f"/workflows/executions/{execution_id}/trace")
        assert trace.status_code == 200, trace.text
        trace_items = trace.json().get("items", [])
        assert trace_items
        serialized_trace = str(trace_items)
        assert "RUNTIME_GOVERNANCE_TEST_SECRET" not in serialized_trace

        audit = client.get(
            "/runtime/audit-logs",
            params={"workflow_execution_id": execution_id, "workflow_id": workflow_id},
        )
        assert audit.status_code == 200, audit.text
        audit_items = audit.json().get("items", [])
        assert audit_items
        assert "RUNTIME_GOVERNANCE_TEST_SECRET" not in str(audit_items)

        for profile_id in profile_ids:
            deleted = client.delete(f"/model-providers/model-profiles/{profile_id}")
            assert deleted.status_code == 204, deleted.text
        for provider_id in provider_ids:
            deleted = client.delete(f"/model-providers/{provider_id}")
            assert deleted.status_code == 204, deleted.text
