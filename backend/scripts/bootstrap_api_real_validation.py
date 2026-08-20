from __future__ import annotations

import os
import sys
import uuid

import httpx


BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TIMEOUT = 20.0


def request(client: httpx.Client, method: str, path: str, **kwargs) -> httpx.Response:
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text}")
    return response


def main() -> int:
    username = os.getenv("API_TEST_USERNAME")
    password = os.getenv("API_TEST_PASSWORD")

    if not username:
        username = f"api_real_test_{uuid.uuid4().hex[:12]}"
    if not password:
        password = f"ApiRealTest!{uuid.uuid4().hex[:16]}"

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        if not os.getenv("API_TEST_USERNAME"):
            request(client, "POST", "/auth/register", json={"username": username, "password": password})

        login = request(client, "POST", "/auth/login", json={"username": username, "password": password})
        token = login.json().get("access_token")
        if not token:
            raise RuntimeError("Login response does not contain access_token")

        client.headers["Authorization"] = f"Bearer {token}"

        workflows = request(client, "GET", "/workflows").json()
        workflow_id = None
        for workflow in workflows:
            if workflow.get("published_version_id"):
                workflow_id = workflow["id"]
                break

        if workflow_id is None:
            created = request(
                client,
                "POST",
                "/workflows",
                json={"name": f"API Real Validation {uuid.uuid4().hex[:8]}", "description": "Automated real API validation fixture"},
            ).json()
            workflow_id = created["id"]
            version = request(
                client,
                "POST",
                f"/workflows/{workflow_id}/versions",
                json={"definition": {"nodes": [], "edges": []}},
            ).json()
            request(client, "POST", f"/workflows/{workflow_id}/versions/{version['id']}/publish")

        execution = request(
            client,
            "POST",
            f"/workflows/{workflow_id}/executions",
            json={"input_data": {"source": "real_api_validation"}},
        ).json()
        execution_id = execution["id"]

    os.environ["ACCESS_TOKEN"] = token
    os.environ["WORKFLOW_ID"] = str(workflow_id)
    os.environ["WORKFLOW_EXECUTION_ID"] = str(execution_id)

    print(f"Real API validation identity: {username}")
    print(f"WORKFLOW_ID={workflow_id}")
    print(f"WORKFLOW_EXECUTION_ID={execution_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
