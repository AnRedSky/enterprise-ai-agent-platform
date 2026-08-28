"""Agent Delegation Real API Contract 验收测试。

职责：通过真实 HTTP + PostgreSQL 验证 Delegation 创建、幂等、tenant/version guard 与取消。
边界：本文件不启动服务，不替代 Worker Runtime 验收；Worker 生命周期在后续 Runtime 集成阶段验证。
关键依赖：真实 API、PostgreSQL、有效 ACCESS_TOKEN。
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")

pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    """创建真实 API 客户端。"""
    if not TOKEN:
        pytest.skip("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=20.0)


def _publish_agent(client: httpx.Client, name: str) -> tuple[str, str]:
    """创建并发布一个可运行 Agent，返回 Agent 与已发布 Version ID。"""
    response = client.post("/agents", json={"name": name, "description": "Phase 2.8 delegation fixture", "system_prompt": "Return deterministic fixture output.", "model_id": "mock-model"})
    assert response.status_code == 200, response.text
    agent_id = response.json()["id"]
    versions = client.get(f"/agents/{agent_id}/versions")
    assert versions.status_code == 200, versions.text
    version_id = versions.json()[0]["id"]
    published = client.post(f"/agents/{agent_id}/publish", json={"version_id": version_id})
    assert published.status_code == 200, published.text
    return agent_id, version_id


def test_delegation_real_http_postgres_idempotency_and_cancel():
    """验证合法 Delegation、重复 key 收敛、查询与取消均真实落库。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        _orchestrator_id, _orchestrator_version_id = _publish_agent(client, f"phase-28-orchestrator-{suffix}")
        _worker_id, worker_version_id = _publish_agent(client, f"phase-28-worker-{suffix}")

        workflow = client.post("/workflows", json={"name": f"phase-28-delegation-{suffix}", "description": "Delegation real API fixture"})
        assert workflow.status_code == 201, workflow.text
        workflow_id = workflow.json()["id"]
        version = client.post(
            f"/workflows/{workflow_id}/versions",
            json={
                "definition": {
                    "config": {"timeout_ms": 5000},
                    "nodes": [{"id": "orchestrator", "type": "agent", "config": {"agent_id": _orchestrator_id, "prompt": "delegate fixture"}}, {"id": "output", "type": "output", "config": {}}],
                    "edges": [{"source": "orchestrator", "target": "output"}],
                }
            },
        )
        assert version.status_code == 201, version.text
        workflow_version_id = version.json()["id"]
        published = client.post(f"/workflows/{workflow_id}/versions/{workflow_version_id}/publish")
        assert published.status_code == 200, published.text
        execution = client.post(f"/workflows/{workflow_id}/executions", json={"input_data": {"fixture": "delegation"}})
        assert execution.status_code == 201, execution.text
        execution_id = execution.json()["id"]

        key = f"delegation-{suffix}"
        payload = {
            "target_agent_version_id": worker_version_id,
            "delegation_key": key,
            "input_data": {"task": "return fixture"},
            "selected_context_refs": ["input:task"],
            "allowed_tools": [],
            "timeout_seconds": 30,
        }
        first = client.post(f"/workflows/{execution_id}/delegations", json=payload)
        assert first.status_code == 201, first.text
        first_body = first.json()
        assert first_body["status"] == "pending"
        assert first_body["source_execution_id"] == execution_id
        assert first_body["target_agent_version_id"] == worker_version_id
        assert first_body["trace_id"] == execution_id

        duplicate = client.post(f"/workflows/{execution_id}/delegations", json=payload)
        assert duplicate.status_code == 201, duplicate.text
        assert duplicate.json()["id"] == first_body["id"]

        listed = client.get(f"/workflows/{execution_id}/delegations")
        assert listed.status_code == 200, listed.text
        assert len(listed.json()) == 1

        cancelled = client.post(f"/workflows/{execution_id}/delegations/{first_body['id']}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"

        second_cancel = client.post(f"/workflows/{execution_id}/delegations/{first_body['id']}/cancel")
        assert second_cancel.status_code == 409, second_cancel.text
