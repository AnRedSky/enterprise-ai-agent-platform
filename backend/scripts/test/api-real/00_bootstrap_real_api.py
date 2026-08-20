from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import httpx

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TIMEOUT = 20.0
ENV_FILE = Path(__file__).with_name(".real_api_context.json")


def request(client, method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text}")
    return response


def create_executable_fixture(client):
    workflow = request(
        client,
        "POST",
        "/workflows",
        json={
            "name": f"API Real Validation {uuid.uuid4().hex[:8]}",
            "description": "Automated real API validation fixture",
        },
    ).json()
    version = request(
        client,
        "POST",
        f"/workflows/{workflow['id']}/versions",
        json={
            "definition": {
                "nodes": [
                    {"id": "input", "type": "input", "config": {}},
                    {"id": "output", "type": "output", "config": {}},
                ],
                "edges": [],
            }
        },
    ).json()
    request(client, "POST", f"/workflows/{workflow['id']}/versions/{version['id']}/publish")
    return workflow["id"]


def create_retry_fixture(client):
    workflow = request(
        client,
        "POST",
        "/workflows",
        json={
            "name": f"API Retry Governance Validation {uuid.uuid4().hex[:8]}",
            "description": "Automated real API node retry governance fixture",
        },
    ).json()
    version = request(
        client,
        "POST",
        f"/workflows/{workflow['id']}/versions",
        json={
            "definition": {
                "config": {"timeout_ms": 30_000},
                "nodes": [
                    {
                        "id": "retry-agent",
                        "type": "agent",
                        "config": {
                            "agent_id": str(uuid.uuid4()),
                            "retry": {
                                "max_attempts": 2,
                                "backoff_ms": 0,
                                "max_backoff_ms": 0,
                                "jitter_ms": 0,
                                "retryable_error_codes": ["HTTP_404"],
                            },
                        },
                    }
                ],
                "edges": [],
            }
        },
    ).json()
    request(client, "POST", f"/workflows/{workflow['id']}/versions/{version['id']}/publish")
    execution = request(
        client,
        "POST",
        f"/workflows/{workflow['id']}/executions",
        json={"input_data": {"source": "real_api_node_retry_validation"}},
    ).json()
    response = client.post(f"/executions/{execution['id']}/run")
    if response.status_code != 404:
        raise RuntimeError(
            f"POST /executions/{execution['id']}/run -> expected 404 after retry fixture failure, "
            f"got {response.status_code}: {response.text}"
        )
    return workflow["id"], execution["id"]


def find_executable_published_workflow(client, workflows):
    for workflow in workflows:
        published_version_id = workflow.get("published_version_id")
        if not published_version_id:
            continue
        versions = request(client, "GET", f"/workflows/{workflow['id']}/versions").json()
        published = next(
            (item for item in versions if str(item.get("id")) == str(published_version_id)),
            None,
        )
        definition = (published or {}).get("definition") or {}
        if definition.get("nodes"):
            return workflow["id"]
    return None


def main():
    username = os.getenv("API_TEST_USERNAME") or f"api_real_test_{uuid.uuid4().hex[:12]}"
    password = os.getenv("API_TEST_PASSWORD") or f"ApiRealTest!{uuid.uuid4().hex[:16]}"
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        if not os.getenv("API_TEST_USERNAME"):
            request(client, "POST", "/auth/register", json={"username": username, "password": password})
        login = request(client, "POST", "/auth/login", json={"username": username, "password": password})
        token = login.json().get("access_token")
        if not token:
            raise RuntimeError("Login response does not contain access_token")
        client.headers["Authorization"] = f"Bearer {token}"

        workflows = request(client, "GET", "/workflows").json()
        workflow_id = find_executable_published_workflow(client, workflows)
        if workflow_id is None:
            workflow_id = create_executable_fixture(client)

        execution = request(
            client,
            "POST",
            f"/workflows/{workflow_id}/executions",
            json={"input_data": {"source": "real_api_validation"}},
        ).json()
        retry_workflow_id, retry_execution_id = create_retry_fixture(client)

    ENV_FILE.write_text(
        json.dumps(
            {
                "ACCESS_TOKEN": token,
                "WORKFLOW_ID": str(workflow_id),
                "WORKFLOW_EXECUTION_ID": str(execution["id"]),
                "RETRY_WORKFLOW_ID": str(retry_workflow_id),
                "RETRY_EXECUTION_ID": str(retry_execution_id),
            }
        ),
        encoding="utf-8",
    )
    print(f"Real API context prepared: {username}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
