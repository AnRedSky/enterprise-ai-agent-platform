from __future__ import annotations

import json
import os
import threading
import uuid
from contextlib import contextmanager
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from .execution_helpers import run_or_observe_execution

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")

pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for usage accounting validation")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20.0,
    )


def _require_context() -> None:
    if not ORGANIZATION_ID:
        pytest.fail("ORGANIZATION_ID is required for usage accounting validation")


@contextmanager
def _fixture_server(model: str):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            body = json.dumps({
                "id": f"usage-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "model": model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "usage accounting success"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1500, "completion_tokens": 500, "total_tokens": 2000},
            }).encode("utf-8")
            self.send_response(200)
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


def test_real_api_persists_governed_usage_and_calculated_cost():
    _require_context()
    suffix = uuid.uuid4().hex[:10]
    provider_id = profile_id = workflow_id = agent_id = None
    model_name = f"usage-accounting-model-{suffix}"

    with _fixture_server(model_name) as endpoint:
        try:
            with _client() as client:
                provider = client.post(
                    "/model-providers",
                    json={
                        "organization_id": ORGANIZATION_ID,
                        "name": f"usage-provider-{suffix}",
                        "provider_type": "openai-compatible",
                        "provider_name": f"usage-provider-{suffix}",
                        "endpoint": endpoint,
                        "credential_ref": f"USAGE_ACCOUNTING_SECRET_{suffix}",
                    },
                )
                assert provider.status_code == 201, provider.text
                provider_id = provider.json()["id"]

                profile = client.post(
                    f"/model-providers/{provider_id}/profiles",
                    json={
                        "name": f"usage-profile-{suffix}",
                        "model_type": "chat",
                        "model_name": model_name,
                        "is_default": True,
                        "parameters": {
                            "pricing": {
                                "pricing_source": "provider_pricing",
                                "pricing_version": "fixture-v1",
                                "input_token_per_1k": 0.002,
                                "output_token_per_1k": 0.004,
                                "request": 0.001,
                            }
                        },
                    },
                )
                assert profile.status_code == 201, profile.text
                profile_id = profile.json()["id"]

                agent = client.post(
                    "/agents",
                    json={
                        "name": f"Usage Accounting Agent {suffix}",
                        "description": "Phase 2.3-G usage accounting fixture",
                        "system_prompt": "Return the provider result without modification.",
                        "model_id": f"legacy-model-{suffix}",
                        "model_profile_id": profile_id,
                    },
                )
                assert agent.status_code == 200, agent.text
                agent_id = agent.json()["id"]

                versions = client.get(f"/agents/{agent_id}/versions")
                assert versions.status_code == 200, versions.text
                publish_agent = client.post(
                    f"/agents/{agent_id}/publish",
                    json={"version_id": versions.json()[0]["id"]},
                )
                assert publish_agent.status_code == 200, publish_agent.text

                workflow = client.post(
                    "/workflows",
                    json={"name": f"Usage Accounting {suffix}", "description": "Phase 2.3-G usage accounting fixture"},
                )
                assert workflow.status_code == 201, workflow.text
                workflow_id = workflow.json()["id"]

                version = client.post(
                    f"/workflows/{workflow_id}/versions",
                    json={
                        "definition": {
                            "config": {"timeout_ms": 5000},
                            "nodes": [
                                {"id": "prepare", "type": "input", "config": {}},
                                {
                                    "id": "usage-agent",
                                    "type": "agent",
                                    "config": {
                                        "agent_id": agent_id,
                                        "prompt": "account this provider request",
                                        "retry": {
                                            "max_attempts": 1,
                                            "backoff_ms": 0,
                                            "max_backoff_ms": 0,
                                            "jitter_ms": 0,
                                            "retryable_error_codes": ["HTTP_503"],
                                        },
                                    },
                                },
                            ],
                            "edges": [{"source": "prepare", "target": "usage-agent"}],
                        }
                    },
                )
                assert version.status_code == 201, version.text
                version_id = version.json()["id"]
                publish_workflow = client.post(f"/workflows/{workflow_id}/versions/{version_id}/publish")
                assert publish_workflow.status_code == 200, publish_workflow.text

                execution = client.post(
                    f"/workflows/{workflow_id}/executions",
                    json={"input_data": {"source": "phase-2.3-g-usage-accounting"}},
                )
                assert execution.status_code == 201, execution.text
                execution_id = execution.json()["id"]

                run_status, persisted_execution = run_or_observe_execution(client, execution_id)
                assert run_status in {200, 409}
                assert persisted_execution["status"] == "completed"

                usage = client.get(
                    "/usage/model",
                    params={"organization_id": ORGANIZATION_ID, "execution_id": execution_id},
                )
                assert usage.status_code == 200, usage.text
                payload = usage.json()
                assert payload["total"] == 1
                assert len(payload["items"]) == 1
                item = payload["items"][0]
                assert item["provider_id"] == provider_id
                assert item["profile_id"] == profile_id
                assert item["model_name"] == model_name
                assert item["outcome"] == "success"
                assert item["prompt_tokens"] == 1500
                assert item["completion_tokens"] == 500
                assert item["total_tokens"] == 2000
                assert item["pricing_version"] == "fixture-v1"
                assert item["cost_units"] == ["request", "input_token", "output_token"]
                assert Decimal(str(item["total_cost"])) == Decimal("0.006")
                assert Decimal(str(payload["total_cost"])) == Decimal("0.006")
                serialized = str(payload)
                assert f"USAGE_ACCOUNTING_SECRET_{suffix}" not in serialized
                assert endpoint not in serialized
        finally:
            with _client() as cleanup:
                if profile_id:
                    cleanup.delete(f"/model-providers/model-profiles/{profile_id}")
                if provider_id:
                    cleanup.delete(f"/model-providers/{provider_id}")
