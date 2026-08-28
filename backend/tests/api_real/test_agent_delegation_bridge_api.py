"""Agent Delegation B2 Worker Execution Bridge Real API 验收测试。

职责：通过真实 HTTP + PostgreSQL 完成 B1 Claim 后，调用现有 Worker Runtime Entry，验证目标 Agent version 被真正执行。
边界：不验证 B3 completion generation fencing；只验证 B2 的 target version、model profile、显式输入、context/tool refs 与 trace bridge。
关键依赖：真实 Backend HTTP、PostgreSQL、Mock Model Provider、现有 Workflow Worker Runtime。
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
from sqlalchemy import select

from app.infrastructure.db.session import SessionLocal
from app.models.agent_delegation import AgentDelegation
from app.models.workflow_execution import WorkflowExecution
from app.services.agent_delegation.claim import claim_delegation
from app.services.agent_delegation.runtime_bridge import AgentDelegationRuntimeBridge
from app.services.workflow_worker import WorkflowWorker
from app.services.workflow_worker.runtime_entry import execute_claimed_execution

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    """创建带自动化测试 Token 的真实 HTTP 客户端。"""
    if not TOKEN:
        pytest.skip("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30.0)


def _publish_agent(client: httpx.Client, name: str) -> tuple[str, str]:
    """创建并发布 Mock Agent，返回 Agent ID 与 published version ID。"""
    response = client.post(
        "/agents",
        json={
            "name": name,
            "description": "Phase 2.8 B2 bridge fixture",
            "system_prompt": "Return the delegated task input unchanged.",
            "model_id": "mock-model",
        },
    )
    assert response.status_code == 200, response.text
    agent_id = response.json()["id"]
    versions = client.get(f"/agents/{agent_id}/versions")
    assert versions.status_code == 200, versions.text
    version_id = versions.json()[0]["id"]
    published = client.post(f"/agents/{agent_id}/publish", json={"version_id": version_id})
    assert published.status_code == 200, published.text
    return agent_id, version_id


@pytest.mark.asyncio
async def test_b2_worker_execution_bridge_runs_target_agent_version():
    """验证 B1 Claim 后现有 Worker Runtime 真正执行 Delegation target Agent。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        orchestrator_id, _ = _publish_agent(client, f"phase-28-b2-orchestrator-{suffix}")
        target_agent_id, target_version_id = _publish_agent(client, f"phase-28-b2-worker-{suffix}")

        workflow = client.post(
            "/workflows",
            json={"name": f"phase-28-b2-{suffix}", "description": "B2 worker bridge real API fixture"},
        )
        assert workflow.status_code == 201, workflow.text
        workflow_id = workflow.json()["id"]
        version = client.post(
            f"/workflows/{workflow_id}/versions",
            json={
                "definition": {
                    "config": {"timeout_ms": 60000},
                    "nodes": [
                        {"id": "orchestrator", "type": "agent", "config": {"agent_id": orchestrator_id, "prompt": "parent workflow must not run"}},
                        {"id": "output", "type": "output", "config": {}},
                    ],
                    "edges": [{"source": "orchestrator", "target": "output"}],
                }
            },
        )
        assert version.status_code == 201, version.text
        workflow_version_id = version.json()["id"]
        published = client.post(f"/workflows/{workflow_id}/versions/{workflow_version_id}/publish")
        assert published.status_code == 200, published.text

        execution = client.post(
            f"/workflows/{workflow_id}/executions",
            json={"input_data": {"fixture": "b2-bridge"}},
        )
        assert execution.status_code == 201, execution.text
        execution_id = execution.json()["id"]

        delegation = client.post(
            f"/workflows/{execution_id}/delegations",
            json={
                "target_agent_version_id": target_version_id,
                "delegation_key": f"b2-{suffix}",
                "input_data": {"prompt": "B2 target execution", "task_id": suffix},
                "selected_context_refs": ["input:task_id"],
                "allowed_tools": ["tool:fixture.read"],
                "timeout_seconds": 60,
            },
        )
        assert delegation.status_code == 201, delegation.text
        delegation_id = delegation.json()["id"]

    async with SessionLocal() as db:
        delegation_row = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == uuid.UUID(delegation_id)))).scalar_one()
        tenant_id = delegation_row.tenant_id
        claimed = await claim_delegation(
            db=db,
            tenant_id=tenant_id,
            delegation_id=delegation_row.id,
            worker_owner=f"b2-worker-{suffix}",
        )
        worker_execution_id = claimed.worker_execution_id
        assert worker_execution_id is not None
        context = await AgentDelegationRuntimeBridge.load(
            db,
            (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == worker_execution_id))).scalar_one(),
        )
        assert context is not None
        assert context.target_agent_version_id == uuid.UUID(target_version_id)
        assert context.target_agent_id == uuid.UUID(target_agent_id)
        assert context.model_profile_id == delegation_row.model_profile_id
        assert context.input_data["task_id"] == suffix
        assert context.selected_context_refs == ("input:task_id",)
        assert context.allowed_tools == ("tool:fixture.read",)
        assert context.trace_id == delegation_row.trace_id

    worker = WorkflowWorker(lease_seconds=60)
    worker.owner = f"b2-worker-{suffix}"
    if not hasattr(worker, "_renew_with_abort_signal"):
        worker._renew_with_abort_signal = worker._renew_lease_once
    await execute_claimed_execution(worker, worker_execution_id)

    async with SessionLocal() as db:
        persisted = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == uuid.UUID(delegation_id)))).scalar_one()
        worker_execution = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == persisted.worker_execution_id))).scalar_one()
        assert worker_execution.workflow_version_id == uuid.UUID(workflow_version_id)
        assert worker_execution.status == "completed"
        assert worker_execution.output_data is not None
        assert worker_execution.output_data["agent_id"] == target_agent_id
        assert worker_execution.output_data["agent_version"] is not None
        assert persisted.status == "running"
