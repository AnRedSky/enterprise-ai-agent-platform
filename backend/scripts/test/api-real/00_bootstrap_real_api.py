from __future__ import annotations

import json
import os
import sys
import time
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


def wait_for_execution_terminal(client, execution_id: str, *, expected_status: str, expected_error: str | None) -> dict:
    """等待 Worker 已经抢占的 Real API Fixture 进入预期终态。"""
    deadline = time.monotonic() + TIMEOUT
    last_payload = None
    while time.monotonic() < deadline:
        response = client.get(f"/workflows/executions/{execution_id}")
        if response.status_code >= 400:
            raise RuntimeError(
                f"GET /workflows/executions/{execution_id} -> {response.status_code}: {response.text}"
            )
        last_payload = response.json()
        if last_payload.get("status") in {"completed", "failed", "cancelled"}:
            if last_payload.get("status") != expected_status:
                raise RuntimeError(
                    f"Worker Fixture persisted unexpected status: {json.dumps(last_payload, ensure_ascii=False)}"
                )
            if expected_error is not None and last_payload.get("error_code") != expected_error:
                raise RuntimeError(
                    f"Worker Fixture persisted unexpected error: {json.dumps(last_payload, ensure_ascii=False)}"
                )
            return last_payload
        time.sleep(0.1)
    raise RuntimeError(
        f"Worker Fixture did not reach expected state within {TIMEOUT}s: "
        f"{json.dumps(last_payload, ensure_ascii=False)}"
    )


def run_fixture_execution(client, execution_id: str, *, expected_status: str, expected_error: str | None, expected_http_status: int) -> dict:
    """触发 Real API Fixture，并兼容独立 Worker 与手动 Run 的合法竞争。"""
    response = client.post(f"/workflows/executions/{execution_id}/run")
    if response.status_code == expected_http_status:
        persisted = request(client, "GET", f"/workflows/executions/{execution_id}").json()
        if persisted.get("status") != expected_status or (
            expected_error is not None and persisted.get("error_code") != expected_error
        ):
            raise RuntimeError(
                f"Manual Run persisted unexpected state: {json.dumps(persisted, ensure_ascii=False)}"
            )
        return persisted
    if response.status_code == 409 and response.json().get("detail") == "只有 pending Execution 可以 Run":
        return wait_for_execution_terminal(
            client,
            execution_id,
            expected_status=expected_status,
            expected_error=expected_error,
        )
    raise RuntimeError(
        f"POST /workflows/executions/{execution_id}/run -> expected HTTP "
        f"{expected_http_status} or Worker ownership race, got {response.status_code}: {response.text}"
    )


def create_user_fixture(client, prefix: str) -> tuple[str, str]:
    username = f"{prefix}_{uuid.uuid4().hex[:12]}"
    password = f"ApiRealTest!{uuid.uuid4().hex[:16]}"
    registered = request(client, "POST", "/auth/register", json={"username": username, "password": password}).json()
    return str(registered["user_id"]), password


def login_token(client, username: str, password: str) -> str:
    login = request(client, "POST", "/auth/login", json={"username": username, "password": password})
    token = login.json().get("access_token")
    if not token:
        raise RuntimeError("Login response does not contain access_token")
    return token


def create_executable_fixture(client):
    workflow = request(client, "POST", "/workflows", json={
        "name": f"API Real Validation {uuid.uuid4().hex[:8]}",
        "description": "Automated real API validation fixture",
    }).json()
    version = request(client, "POST", f"/workflows/{workflow['id']}/versions", json={
        "definition": {"nodes": [
            {"id": "input", "type": "input", "config": {}},
            {"id": "output", "type": "output", "config": {}},
        ], "edges": [{"source": "input", "target": "output"}]}
    }).json()
    request(client, "POST", f"/workflows/{workflow['id']}/versions/{version['id']}/publish")
    return workflow["id"]


def create_trigger_fixture(client, workflow_id):
    trigger = request(client, "POST", f"/workflows/{workflow_id}/triggers", json={
        "name": f"api-real-manual-{uuid.uuid4().hex[:8]}",
        "trigger_type": "manual",
        "config": {"source": "real_api_trigger_validation"},
    }).json()
    return trigger["id"]


def create_retry_agent(client, *, model_id="mock-http-404", name_prefix="API Retry Agent"):
    agent = request(client, "POST", "/agents", json={
        "name": f"{name_prefix} {uuid.uuid4().hex[:8]}",
        "description": "Automated real API node retry governance fixture agent",
        "system_prompt": "You are a deterministic validation agent.",
        "model_id": model_id,
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
            "nodes": [
                {"id": "retry-agent", "type": "agent", "config": node_config},
                {"id": "retry-output", "type": "output", "config": {}},
            ],
            "edges": [{"source": "retry-agent", "target": "retry-output"}],
        }
    }).json()
    request(client, "POST", f"/workflows/{workflow['id']}/versions/{version['id']}/publish")
    execution = request(client, "POST", f"/workflows/{workflow['id']}/executions", json={
        "input_data": {"source": "real_api_retry_boundary_validation"}
    }).json()
    run_fixture_execution(client, execution["id"], expected_status=expected_status,
                          expected_error=expected_error, expected_http_status=expected_http_status)
    return workflow["id"], execution["id"]


def create_circuit_fixture(client, agent_id, *, name, circuit_key, runtime_config, retry_config,
                           expected_error="CIRCUIT_OPEN", expected_http_status=503,
                           recovery_timeout_ms=1000):
    workflow = request(client, "POST", "/workflows", json={
        "name": f"{name} {uuid.uuid4().hex[:8]}",
        "description": "Automated real API Circuit Breaker boundary fixture",
    }).json()
    node_config = {
        "agent_id": agent_id,
        "prompt": "Trigger deterministic Circuit Breaker boundary validation.",
        "retry": retry_config,
        "circuit_breaker": {
            "enabled": True, "key": circuit_key, "failure_threshold": 1,
            "recovery_timeout_ms": recovery_timeout_ms, "half_open_max_calls": 1,
        },
    }
    version = request(client, "POST", f"/workflows/{workflow['id']}/versions", json={
        "definition": {
            "config": runtime_config,
            "nodes": [
                {"id": "circuit-agent", "type": "agent", "config": node_config},
                {"id": "circuit-output", "type": "output", "config": {}},
            ],
            "edges": [{"source": "circuit-agent", "target": "circuit-output"}],
        }
    }).json()
    request(client, "POST", f"/workflows/{workflow['id']}/versions/{version['id']}/publish")
    execution = request(client, "POST", f"/workflows/{workflow['id']}/executions", json={
        "input_data": {"source": "real_api_circuit_breaker_validation"}
    }).json()
    run_fixture_execution(client, execution["id"], expected_status="failed",
                          expected_error=expected_error, expected_http_status=expected_http_status)
    return workflow["id"], execution["id"]


def create_circuit_recovery_fixture(client, agent_id, *, name, circuit_key, recovery_timeout_ms):
    workflow = request(client, "POST", "/workflows", json={
        "name": f"{name} {uuid.uuid4().hex[:8]}",
        "description": "Automated real API Circuit Breaker recovery fixture",
    }).json()
    node_config = {
        "agent_id": agent_id,
        "prompt": "Verify Circuit Breaker HALF_OPEN recovery success.",
        "retry": {"max_attempts": 1, "backoff_ms": 0, "max_backoff_ms": 0,
                   "jitter_ms": 0, "retryable_error_codes": ["HTTP_503"]},
        "circuit_breaker": {"enabled": True, "key": circuit_key, "failure_threshold": 1,
                             "recovery_timeout_ms": recovery_timeout_ms, "half_open_max_calls": 1},
    }
    version = request(client, "POST", f"/workflows/{workflow['id']}/versions", json={
        "definition": {
            "config": {"timeout_ms": 30_000},
            "nodes": [
                {"id": "circuit-recovery-agent", "type": "agent", "config": node_config},
                {"id": "circuit-recovery-output", "type": "output", "config": {}},
            ],
            "edges": [{"source": "circuit-recovery-agent", "target": "circuit-recovery-output"}],
        }
    }).json()
    request(client, "POST", f"/workflows/{workflow['id']}/versions/{version['id']}/publish")
    return workflow["id"]


def create_retry_boundary_fixtures(client, agent_id):
    retry_workflow_id, retry_execution_id = create_retry_fixture(
        client, agent_id, name="API Retry Governance Validation",
        runtime_config={"timeout_ms": 30_000, "retry_budget": {"max_retries": 1}},
    )
    budget_workflow_id, budget_execution_id = create_retry_fixture(
        client, agent_id, name="API Retry Budget Exhausted Validation",
        runtime_config={"timeout_ms": 30_000, "retry_budget": {"max_retries": 0}},
    )
    deadline_workflow_id, deadline_execution_id = create_retry_fixture(
        client, agent_id, name="API Retry Deadline Validation",
        runtime_config={"timeout_ms": 1000, "retry_budget": {"max_retries": 1}},
        retry_config={"max_attempts": 3, "backoff_ms": 2000, "max_backoff_ms": 2000,
                      "jitter_ms": 0, "retryable_error_codes": ["HTTP_404"]},
        expected_error="WORKFLOW_TIMEOUT", expected_http_status=504,
    )
    return {"retry_workflow_id": retry_workflow_id, "retry_execution_id": retry_execution_id,
            "budget_workflow_id": budget_workflow_id, "budget_execution_id": budget_execution_id,
            "deadline_workflow_id": deadline_workflow_id, "deadline_execution_id": deadline_execution_id}


def create_circuit_breaker_fixtures(client):
    circuit_key = f"real-api-circuit-{uuid.uuid4().hex[:8]}"
    circuit_recovery_timeout_ms = 10_000
    failing_agent_id = create_retry_agent(client, model_id="mock-http-503", name_prefix="API Circuit Failure Agent")
    recovery_agent_id = create_retry_agent(client, model_id="mock-slow-success", name_prefix="API Circuit Recovery Agent")
    open_workflow_id, open_execution_id = create_circuit_fixture(
        client, failing_agent_id, name="API Circuit Breaker Open Validation", circuit_key=circuit_key,
        runtime_config={"timeout_ms": 30_000, "retry_budget": {"max_retries": 1}},
        retry_config={"max_attempts": 2, "backoff_ms": 0, "max_backoff_ms": 0, "jitter_ms": 0,
                      "retryable_error_codes": ["HTTP_503"]}, recovery_timeout_ms=circuit_recovery_timeout_ms)
    recovery_workflow_id = create_circuit_recovery_fixture(
        client, recovery_agent_id, name="API Circuit Breaker Recovery Validation",
        circuit_key=circuit_key, recovery_timeout_ms=circuit_recovery_timeout_ms)
    return {"circuit_open_workflow_id": open_workflow_id, "circuit_open_execution_id": open_execution_id,
            "circuit_recovery_workflow_id": recovery_workflow_id}


def create_organization_fixture(client, owner_username: str, owner_password: str) -> dict[str, str]:
    response = client.post("/organizations", json={"name": f"API Real Organization {uuid.uuid4().hex[:8]}"})
    if response.status_code == 409 and response.json().get("detail") == "当前 Tenant 已存在 Organization":
        organizations = request(client, "GET", "/organizations").json()
        if not organizations:
            raise RuntimeError("Tenant reports an existing Organization, but GET /organizations returned none")
        organization = organizations[0]
        return {"organization_id": str(organization["id"]), "membership_id": "", "member_user_id": "",
                "member_access_token": ""}
    if response.status_code >= 400:
        raise RuntimeError(f"POST /organizations -> {response.status_code}: {response.text}")
    organization = response.json()
    member_username = f"api_real_org_member_{uuid.uuid4().hex[:12]}"
    member_password = f"ApiRealTest!{uuid.uuid4().hex[:16]}"
    member = request(client, "POST", "/auth/register", json={"username": member_username, "password": member_password}).json()
    membership = request(client, "POST", f"/organizations/{organization['id']}/members", json={
        "user_id": member["user_id"], "role": "admin",
    }).json()
    member_token = login_token(client, member_username, member_password)
    return {"organization_id": str(organization["id"]), "membership_id": str(membership["id"]),
            "member_user_id": str(member["user_id"]), "member_access_token": member_token}


def main():
    username = os.getenv("API_TEST_USERNAME") or f"api_real_test_{uuid.uuid4().hex[:12]}"
    password = os.getenv("API_TEST_PASSWORD") or f"ApiRealTest!{uuid.uuid4().hex[:16]}"
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        if not os.getenv("API_TEST_USERNAME"):
            request(client, "POST", "/auth/register", json={"username": username, "password": password})
        token = login_token(client, username, password)
        client.headers["Authorization"] = f"Bearer {token}"
        organization = create_organization_fixture(client, username, password)
        workflow_id = create_executable_fixture(client)
        trigger_id = create_trigger_fixture(client, workflow_id)
        execution = request(client, "POST", f"/workflows/{workflow_id}/executions", json={"input_data": {"source": "real_api_validation"}}).json()
        retry_agent_id = create_retry_agent(client)
        boundary = create_retry_boundary_fixtures(client, retry_agent_id)
        circuit = create_circuit_breaker_fixtures(client)

    context = {"ACCESS_TOKEN": token, "WORKFLOW_ID": str(workflow_id), "WORKFLOW_EXECUTION_ID": str(execution["id"]),
               "TRIGGER_WORKFLOW_ID": str(workflow_id), "TRIGGER_ID": str(trigger_id),
               "RETRY_WORKFLOW_ID": str(boundary["retry_workflow_id"]), "RETRY_EXECUTION_ID": str(boundary["retry_execution_id"]),
               "RETRY_BUDGET_WORKFLOW_ID": str(boundary["budget_workflow_id"]), "RETRY_BUDGET_EXECUTION_ID": str(boundary["budget_execution_id"]),
               "RETRY_DEADLINE_WORKFLOW_ID": str(boundary["deadline_workflow_id"]), "RETRY_DEADLINE_EXECUTION_ID": str(boundary["deadline_execution_id"]),
               "CIRCUIT_OPEN_WORKFLOW_ID": str(circuit["circuit_open_workflow_id"]), "CIRCUIT_OPEN_EXECUTION_ID": str(circuit["circuit_open_execution_id"]),
               "CIRCUIT_RECOVERY_WORKFLOW_ID": str(circuit["circuit_recovery_workflow_id"]),
               "ORGANIZATION_ID": organization["organization_id"], "ORGANIZATION_MEMBERSHIP_ID": organization["membership_id"],
               "ORGANIZATION_MEMBER_USER_ID": organization["member_user_id"], "ORGANIZATION_MEMBER_ACCESS_TOKEN": organization["member_access_token"]}
    ENV_FILE.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Real API context prepared: {ENV_FILE.stem}_{uuid.uuid4().hex[:12]}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Real API bootstrap failed: {exc}", file=sys.stderr)
        raise
