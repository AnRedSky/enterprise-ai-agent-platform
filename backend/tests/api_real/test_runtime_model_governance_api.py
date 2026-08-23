from __future__ import annotations

import json
import os
import threading
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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


@contextmanager
def _openai_fixture_server(status_code: int, content: str, *, model: str):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            payload = {
                "id": f"fixture-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "model": model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_runtime_governed_fallback_success_uses_real_http_provider_and_records_attempt_trace():
    _require_context()
    suffix = uuid.uuid4().hex[:10]
    provider_ids: list[str] = []
    profile_ids: list[str] = []

    with _openai_fixture_server(503, "provider failure", model="fixture-failing-model") as failing_endpoint, \
            _openai_fixture_server(200, "governed fallback success", model="fixture-success-model") as success_endpoint:
        try:
            with _client() as client:
                for name, provider_name, endpoint, model_name in (
                    (f"a-governed-fallback-failing-{suffix}", "a-governed-fallback-failing", failing_endpoint, "fixture-failing-model"),
                    (f"b-governed-fallback-success-{suffix}", "b-governed-fallback-success", success_endpoint, "fixture-success-model"),
                ):
                    provider = client.post(
                        "/model-providers",
                        json={
                            "organization_id": ORGANIZATION_ID,
                            "name": name,
                            "provider_type": "openai-compatible",
                            "provider_name": provider_name,
                            "endpoint": endpoint,
                            "credential_ref": f"GOVERNED_FALLBACK_SECRET_{suffix}",
                        },
                    )
                    assert provider.status_code == 201, provider.text
                    provider_id = provider.json()["id"]
                    provider_ids.append(provider_id)

                    profile = client.post(
                        f"/model-providers/{provider_id}/profiles",
                        json={
                            "name": f"chat-{suffix}-{provider_name}",
                            "model_type": "chat",
                            "model_name": model_name,
                            "is_default": True,
                        },
                    )
                    assert profile.status_code == 201, profile.text
                    profile_ids.append(profile.json()["id"])

                agent = client.post(
                    "/agents",
                    json={
                        "name": f"Governed Fallback Success Agent {suffix}",
                        "description": "Phase 2.3-E deterministic real HTTP provider fixture",
                        "system_prompt": "You are a deterministic provider governance validation agent.",
                        "model_id": f"legacy-model-{suffix}",
                    },
                )
                assert agent.status_code == 200, agent.text
                agent_id = agent.json()["id"]

                versions = client.get(f"/agents/{agent_id}/versions")
                assert versions.status_code == 200, versions.text
                published = client.post(
                    f"/agents/{agent_id}/publish",
                    json={"version_id": versions.json()[0]["id"]},
                )
                assert published.status_code == 200, published.text

                workflow = client.post(
                    "/workflows",
                    json={
                        "name": f"Governed Fallback Success {suffix}",
                        "description": "Phase 2.3-E deterministic real HTTP provider fixture",
                    },
                )
                assert workflow.status_code == 201, workflow.text
                workflow_id = workflow.json()["id"]

                version = client.post(
                    f"/workflows/{workflow_id}/versions",
                    json={
                        "definition": {
                            "config": {"timeout_ms": 5000},
                            "nodes": [{
                                "id": "governed-fallback-agent",
                                "type": "agent",
                                "config": {
                                    "agent_id": agent_id,
                                    "prompt": "verify deterministic governed fallback success",
                                    "model_governance": {
                                        "allowed_provider_ids": provider_ids,
                                    },
                                    "retry": {
                                        "max_attempts": 1,
                                        "backoff_ms": 0,
                                        "max_backoff_ms": 0,
                                        "jitter_ms": 0,
                                        "retryable_error_codes": ["HTTP_503"],
                                    },
                                },
                            }],
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
                    json={"input_data": {"source": "phase-2.3-e-real-provider-fallback"}},
                )
                assert execution.status_code == 201, execution.text
                execution_id = execution.json()["id"]

                run = client.post(f"/workflows/executions/{execution_id}/run")
                assert run.status_code == 200, run.text
                assert run.json()["status"] == "completed"

                trace = client.get(f"/workflows/executions/{execution_id}/trace")
                assert trace.status_code == 200, trace.text
                trace_items = trace.json()["items"]
                invocation_events = [item for item in trace_items if item["event_type"] == "model.invocation"]
                assert len(invocation_events) == 2

                first, second = invocation_events
                assert first["data"]["provider_id"] == provider_ids[0]
                assert first["data"]["outcome"] == "failed"
                assert first["data"]["fallback_reason"] == "provider_5xx"
                assert first["data"]["request_id"]
                assert first["data"]["trace_id"] == execution_id

                assert second["data"]["provider_id"] == provider_ids[1]
                assert second["data"]["outcome"] == "success"
                assert second["data"]["request_id"]
                assert second["data"]["request_id"] != first["data"]["request_id"]
                assert second["data"]["trace_id"] == execution_id
                assert second["data"]["usage"] == {
                    "prompt_tokens": 11,
                    "completion_tokens": 7,
                    "total_tokens": 18,
                }

                serialized_trace = str(trace_items)
                assert f"GOVERNED_FALLBACK_SECRET_{suffix}" not in serialized_trace
                assert "endpoint" not in second["data"]
                assert "credential_ref" not in second["data"]
        finally:
            with _client() as cleanup:
                for profile_id in profile_ids:
                    cleanup.delete(f"/model-providers/model-profiles/{profile_id}")
                for provider_id in provider_ids:
                    cleanup.delete(f"/model-providers/{provider_id}")


def test_runtime_uses_published_model_profile_and_records_usage_identity_without_mock_fallback():
    _require_context()
    suffix = uuid.uuid4().hex[:10]
    provider_ids: list[str] = []
    profile_ids: list[str] = []
    agent_id = None
    workflow_id = None

    try:
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
                    "parameters": {"timeout_seconds": 0.25},
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

            versions = client.get(f"/agents/{agent_id}/versions")
            assert versions.status_code == 200, versions.text
            version_items = versions.json()
            assert version_items
            published = client.post(
                f"/agents/{agent_id}/publish",
                json={"version_id": version_items[0]["id"]},
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
                                        "retryable_error_codes": ["HTTP_503"],
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
            assert payload["error_code"] == "HTTP_500"

            trace = client.get(f"/workflows/executions/{execution_id}/trace")
            assert trace.status_code == 200, trace.text
            trace_items = trace.json()["items"]
            invocation_events = [item for item in trace_items if item["event_type"] == "model.invocation"]
            assert invocation_events
            invocation = invocation_events[-1]
            identity = invocation["data"]
            assert identity["organization_id"] == ORGANIZATION_ID
            assert identity["provider_id"] == provider_id
            assert identity["profile_id"] == profile_id
            assert identity["model_type"] == "chat"
            assert identity["request_id"]
            assert identity["trace_id"] == execution_id
            assert identity["outcome"] == "failed"
            assert identity["fallback_reason"] == "connectivity"
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
    finally:
        if TOKEN and (provider_ids or profile_ids):
            with _client() as cleanup:
                for profile_id in profile_ids:
                    cleanup.delete(f"/model-providers/model-profiles/{profile_id}")
                for provider_id in provider_ids:
                    cleanup.delete(f"/model-providers/{provider_id}")
