"""Agent Delegation B1 Atomic Claim Real API 验收测试。

职责：通过真实 HTTP 创建 Delegation，再通过真实 PostgreSQL 会话验证 Atomic Claim、
tenant boundary、重复 Claim 拒绝与唯一 Worker Execution 绑定。
边界：不执行 target Agent Runtime；B2 Worker Execution Bridge 在后续阶段验收。
关键依赖：真实 API、PostgreSQL、有效 ACCESS_TOKEN、已执行 Alembic head。
"""

from __future__ import annotations

import asyncio
import os
import uuid

import httpx
import pytest
from sqlalchemy import func, select

from app.infrastructure.db.session import SessionLocal
from app.models.agent_delegation import AgentDelegation
from app.models.workflow_execution import WorkflowExecution
from app.services.agent_delegation.claim import claim_delegation

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")

pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    """创建真实 HTTP 客户端。

    Returns:
        httpx.Client: 携带真实访问令牌的 HTTP 客户端。

    Raises:
        pytest.skip: 未提供 ACCESS_TOKEN 时跳过真实 API 场景。
    """
    if not TOKEN:
        pytest.skip("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30.0)


def _publish_agent(client: httpx.Client, name: str) -> tuple[str, str]:
    """创建并发布一个可运行 Agent。

    Args:
        client: 已认证的真实 HTTP 客户端。
        name: Agent 名称。

    Returns:
        tuple[str, str]: Agent ID 与已发布 Agent Version ID。
    """
    response = client.post(
        "/agents",
        json={
            "name": name,
            "description": "Phase 2.8 B1 atomic claim fixture",
            "system_prompt": "Return deterministic fixture output.",
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


async def _concurrent_claim(tenant_id, delegation_id: str):
    """使用两个独立数据库会话并发竞争同一个 Delegation。

    Args:
        tenant_id: Delegation 所属租户 ID。
        delegation_id: 待竞争 Claim 的 Delegation ID。

    Returns:
        list[tuple[str, str | None]]: 每个 Worker 的结果，成功项包含 execution ID，失败项包含错误文本。
    """
    async def _run(owner: str):
        async with SessionLocal() as db:
            try:
                item = await claim_delegation(
                    db=db,
                    tenant_id=tenant_id,
                    delegation_id=uuid.UUID(delegation_id),
                    worker_owner=owner,
                )
                return owner, str(item.worker_execution_id)
            except Exception as exc:  # noqa: BLE001 - 验证第二个竞争者必须失败
                return owner, f"{type(exc).__name__}: {exc}"

    return await asyncio.gather(_run("b1-worker-a"), _run("b1-worker-b"))


def test_b1_atomic_claim_allows_one_worker_and_persists_one_execution():
    """验证两个真实数据库会话竞争同一 Delegation 时只能一个 Worker 成功。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        orchestrator_id, _ = _publish_agent(client, f"phase-28-b1-orchestrator-{suffix}")
        _, worker_version_id = _publish_agent(client, f"phase-28-b1-worker-{suffix}")

        workflow = client.post(
            "/workflows",
            json={"name": f"phase-28-b1-{suffix}", "description": "B1 atomic claim real API fixture"},
        )
        assert workflow.status_code == 201, workflow.text
        workflow_id = workflow.json()["id"]
        version = client.post(
            f"/workflows/{workflow_id}/versions",
            json={
                "definition": {
                    "config": {"timeout_ms": 60000},
                    "nodes": [
                        {"id": "orchestrator", "type": "agent", "config": {"agent_id": orchestrator_id, "prompt": "delegate fixture"}},
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
            json={"input_data": {"fixture": "b1-atomic-claim"}},
        )
        assert execution.status_code == 201, execution.text
        execution_id = execution.json()["id"]

        delegation = client.post(
            f"/workflows/{execution_id}/delegations",
            json={
                "target_agent_version_id": worker_version_id,
                "delegation_key": f"b1-{suffix}",
                "input_data": {"task": "atomic claim"},
                "selected_context_refs": ["input:task"],
                "allowed_tools": [],
                "timeout_seconds": 60,
            },
        )
        assert delegation.status_code == 201, delegation.text
        delegation_id = delegation.json()["id"]

    async def _read_identity():
        async with SessionLocal() as db:
            item = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == uuid.UUID(delegation_id)))).scalar_one()
            return item.tenant_id

    tenant_id = asyncio.run(_read_identity())
    results = asyncio.run(_concurrent_claim(tenant_id, delegation_id))

    success = [item for item in results if not item[1].startswith("HTTPException")]
    failures = [item for item in results if item not in success]
    assert len(success) == 1, results
    assert len(failures) == 1, results

    async def _read_persisted_state():
        async with SessionLocal() as db:
            delegation_row = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == uuid.UUID(delegation_id)))).scalar_one()
            executions = list((await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == delegation_row.worker_execution_id))).scalars().all())
            count = int((await db.execute(select(func.count(WorkflowExecution.id)).where(WorkflowExecution.id == delegation_row.worker_execution_id))).scalar_one())
            return delegation_row, executions, count

    persisted, executions, count = asyncio.run(_read_persisted_state())
    assert persisted.status == "running"
    assert persisted.worker_execution_id is not None
    assert len(executions) == 1
    assert count == 1
    assert persisted.worker_execution_id == uuid.UUID(success[0][1])
    assert executions[0].tenant_id == persisted.tenant_id
    assert executions[0].worker_owner == success[0][0]

    async def _second_claim():
        async with SessionLocal() as db:
            try:
                await claim_delegation(
                    db=db,
                    tenant_id=tenant_id,
                    delegation_id=uuid.UUID(delegation_id),
                    worker_owner="b1-worker-c",
                )
            except Exception as exc:  # noqa: BLE001 - 预期 409
                return type(exc).__name__, str(exc)
            return None

    second = asyncio.run(_second_claim())
    assert second is not None
    assert "不能再次 Claim" in second[1]
