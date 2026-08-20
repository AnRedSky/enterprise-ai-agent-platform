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
    workflow = request(client, "POST", "/workflows", json={
        "name": f"API Real Validation {uuid.uuid4().hex[:8]}",
        "description": "Automated real API validation fixture",
    }).json()
    version = request(client, "POST", f"/workflows/{workflow['id']}/versions", json={
        "definition": {"nodes": [
            {"id": "input", "type": "input", "config": {}},
            {"id": "output", "type": "output", "config": {}},
        ], "edges": []}
    }).json()
    request(client, "POST", f"/workflows/{workflow['id']}/versions/{version['id']}/publish")
    return workflow["id"]


def create_retry_agent(client):
    agent = request(client, "POST", "/agents", json={
        "name": f"API Retry Agent {uuid.uuid4().hex[:8]}",
        "description": "Automated real API node retry governance fixture agent",
        "system_prompt": "You are a deterministic validation agent.",
        "model_id": "mock-http-404",
    }).json()
    versions = request(client, "GET", f"/agents/{agent['id']}/versions").json()
    if not versions:
        raise RuntimeError(f"Agent {agent['id']} was created without a version")
    request(client, "POST", f"/agents/{agent['id']}/publish", json={"version_id": versions[0]["id"]})
    return agent["id"]


def create_retry_fixture(client, agent_id, *, name, runtime_config=None, retry_config=None,
                         expected_status="failed", expected_error="HTTP_404", expected_http_status=404):
    workflow = request(client, "POST", "/workflows", json={
        "name": f"{name} {uuid.uuid4().hex[:8]}",
        "description": "Automated real API retry boundary fixture",
    }).json()
    node_config = {
        "agent_id": agent_id,
        "prompt": "Trigger deterministic node retry boundary validation.",
        "retry": retry_config or {
            "max_attempts": 2,
            "backoff_ms": 0,
            "max_backoff_ms": 0,
            "jitter_ms": 0,
            "retryable_error_codes": ["HTTP_404"],
        },
    }
    version = request(client, "POST", f"/workflows/{workflow['id']}/versions", json={
        "definition": {
            "config": runtime_config or {"timeout_ms": 30_000},
            "nodes": [{"id": "retry-agent", "type": "agent", "config": node_config}],
            "edges": [],
        }
    }).json()
    request(client, "POST", f"/workflows/{workflow['id']}/versions/{version['id']}/publish")
    execution = request(client, "POST", f"/workflows/{workflow['id']}/executions", json={
        "input_data": {"source": "real_api_retry_boundary_validation"}
    }).json()
    response = client.post(f"/workflows/executions/{execution['id']}/run")
    if response.status_code != expected_http_status:
        raise RuntimeError(
            f"POST /workflows/executions/{execution['id']}/run -> expected HTTP "
            f"{expected_http_status}, got {response.status_code}: {response.text}"
        )
    persisted = request(client, "GET", f"/workflows/executions/{execution['id']}").json()
    if persisted.get("status") != expected_status or persisted.get("error_code") != expected_error:
        raise RuntimeError(f"Retry boundary fixture persisted unexpected state: {json.dumps(persisted, ensure_ascii=False)}")
    return workflow["id"], execution["id"]


def create_retry_boundary_fixtures(client, agent_id):
    retry_workflow_id, retry_execution_id = create_retry_fixture(
        client, agent_id, name="API Retry Governance Validation"
    )
    budget_workflow_id, budget_execution_id = create_retry_fixture(
        client, agent_id,
        name="API Retry Budget Exhausted Validation",
        runtime_config={"timeout_ms": 30_000, "retry_budget": {"max_retries": 0}},
    )
    deadline_workflow_id, deadline_execution_id = create_retry_fixture(
        client, agent_id,
        name="API Retry Deadline Validation",
        runtime_config={"timeout_ms": 10},
        retry_config={
            "max_attempts": 3,
            "backoff_ms": 100,
            "max_backoff_ms": 100,
            "jitter_ms": 0,
            "retryable_error_codes": ["HTTP_404"],
        },
        expected_error="WORKFLOW_TIMEOUT",
        expected_http_status=504,
    )
    return {
        "retry_workflow_id": retry_workflow_id,
        "retry_execution_id": retry_execution_id,
        "budget_workflow_id": budget_workflow_id,
        "budget_execution_id": budget_execution_id,
        "deadline_workflow_id": deadline_workflow_id,
        "deadline_execution_id": deadline_execution_id,
    }


def find_executable_published_workflow(client, workflows):
    for workflow in workflows:
        published_version_id = workflow.get("published_version_id")
        if not published_version_id:
            continue
        versions = request(client, "GET", f"/workflows/{workflow['id']}/versions").json()
        published = next((item for item in versions if str(item.get("id")) == str(published_version_id)), None)
        if ((published or {}).get("definition") or {}).get("nodes"):
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
        workflow_id = find_executable_published_workflow(client, workflows) or create_executable_fixture(client)
        execution = request(client, "POST", f"/workflows/{workflow_id}/executions", json={"input_data": {"source": "real_api_validation"}}).json()
        agent_id = create_retry_agent(client)
        boundary = create_retry_boundary_fixtures(client, agent_id)

    context = {
        "ACCESS_TOKEN": token,
        "WORKFLOW_ID": str(workflow_id),
        "WORKFLOW_EXECUTION_ID": str(execution["id"]),
        "RETRY_WORKFLOW_ID": str(boundary["retry_workflow_id"]),
        "RETRY_EXECUTION_ID": str(boundary["retry_execution_id"]),
        "RETRY_BUDGET_WORKFLOW_ID": str(boundary["budget_workflow_id"]),
        "RETRY_BUDGET_EXECUTION_ID": str(boundary["budget_execution_id"]),
        "RETRY_DEADLINE_WORKFLOW_ID": str(boundary["deadline_workflow_id"]),
        "RETRY_DEADLINE_EXECUTION_ID": str(boundary["deadline_execution_id"]),
    }
    ENV_FILE.write_text(json.dumps(context), encoding="utf-8")
    print(f"Real API context prepared: {username}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
