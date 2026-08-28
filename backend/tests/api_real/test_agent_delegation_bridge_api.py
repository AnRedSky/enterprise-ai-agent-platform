"""Agent Delegation B2/B3 Worker Runtime Real API 验收测试。

职责：通过真实 HTTP + PostgreSQL 验证 B1 Claim、B2 target Agent Runtime 与 B3 Delegation completion/failure generation fencing。
边界：不验证 B4 timeout/cancel/parent semantics；失败场景仅验证 Worker Execution 已持久化失败后的 Delegation 收敛。
关键依赖：真实 Backend HTTP、PostgreSQL、Mock Model Provider、现有 Workflow Worker Runtime。
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.infrastructure.db.session import SessionLocal
from app.models.agent_delegation import AgentDelegation
from app.models.model_provider import ModelProfile, ModelProvider
from app.models.workflow_execution import WorkflowExecution
from app.services.agent_delegation.claim import claim_delegation
from app.services.agent_delegation.completion import complete_delegation, fail_delegation
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


def _create_delegation(client: httpx.Client, suffix: str) -> tuple[str, str, str, str, str]:
    """创建真实 Workflow/Execution/Delegation Fixture，并返回关键标识。"""
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
    return delegation.json()["id"], target_agent_id, target_version_id, workflow_version_id, execution_id


async def _bind_deterministic_mock_profile(db, delegation_id: uuid.UUID, suffix: str) -> uuid.UUID:
    """为真实验收 Delegation 创建组织内独立 Mock Profile，避免依赖本地默认 Provider。

    Args:
        db: 当前真实 PostgreSQL 异步会话。
        delegation_id: 待执行 Delegation ID。
        suffix: 测试唯一后缀，用于避免 Provider/Profile 名称冲突。

    Returns:
        新建的 Mock Model Profile ID。

    Raises:
        AssertionError: 当前 Delegation 未绑定可用于推导组织边界的 Model Profile。
    """
    delegation = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_id))).scalar_one()
    assert delegation.model_profile_id is not None
    source_profile = (
        await db.execute(select(ModelProfile).where(ModelProfile.id == delegation.model_profile_id))
    ).scalar_one()
    source_provider = (
        await db.execute(select(ModelProvider).where(ModelProvider.id == source_profile.provider_id))
    ).scalar_one()

    mock_provider = ModelProvider(
        organization_id=source_provider.organization_id,
        name=f"phase-28-mock-provider-{suffix}",
        provider_type="mock",
        provider_name="phase-28-real-gate",
        enabled=True,
        metadata_json={"purpose": "phase-2.8-real-gate"},
    )
    db.add(mock_provider)
    await db.flush()

    mock_profile = ModelProfile(
        provider_id=mock_provider.id,
        name=f"phase-28-mock-profile-{suffix}",
        model_type=source_profile.model_type,
        model_name="mock-model",
        capabilities=source_profile.capabilities or {},
        parameters={},
        enabled=True,
        is_default=False,
    )
    db.add(mock_profile)
    await db.flush()
    delegation.model_profile_id = mock_profile.id
    await db.commit()
    return mock_profile.id


@pytest.mark.asyncio
async def test_b2_worker_execution_bridge_runs_target_agent_version():
    """验证 B1 Claim 后现有 Worker Runtime 真正执行 Delegation target Agent，并完成 Delegation。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        delegation_id, target_agent_id, target_version_id, workflow_version_id, _ = _create_delegation(client, suffix)

    async with SessionLocal() as db:
        delegation_uuid = uuid.UUID(delegation_id)
        await _bind_deterministic_mock_profile(db, delegation_uuid, suffix)
        delegation_row = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_uuid))).scalar_one()
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
        assert persisted.status == "completed"
        assert persisted.ended_at is not None


@pytest.mark.asyncio
async def test_b3_stale_worker_generation_cannot_complete_delegation():
    """验证旧 Worker generation 不能提前收敛当前 Delegation。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        delegation_id, _, _, _, _ = _create_delegation(client, f"b3-{suffix}")

    async with SessionLocal() as db:
        delegation_row = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == uuid.UUID(delegation_id)))).scalar_one()
        delegation_uuid = delegation_row.id
        claimed = await claim_delegation(
            db=db,
            tenant_id=delegation_row.tenant_id,
            delegation_id=delegation_uuid,
            worker_owner=f"b3-worker-{suffix}",
        )
        assert claimed.worker_execution_id is not None
        stale_worker_execution_id = uuid.uuid4()
        with pytest.raises(HTTPException) as exc_info:
            await complete_delegation(
                db=db,
                tenant_id=delegation_row.tenant_id,
                delegation_id=delegation_uuid,
                worker_execution_id=stale_worker_execution_id,
            )
        assert exc_info.value.status_code == 409
        await db.rollback()
        persisted = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_uuid))).scalar_one()
        assert persisted.status == "running"
        assert persisted.worker_execution_id == claimed.worker_execution_id


@pytest.mark.asyncio
async def test_b3_failed_worker_execution_closes_delegation():
    """验证 Worker Execution 已持久化失败后，当前 generation 能收敛 Delegation failed。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        delegation_id, _, _, _, _ = _create_delegation(client, f"b3-failure-{suffix}")

    async with SessionLocal() as db:
        delegation_row = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == uuid.UUID(delegation_id)))).scalar_one()
        claimed = await claim_delegation(
            db=db,
            tenant_id=delegation_row.tenant_id,
            delegation_id=delegation_row.id,
            worker_owner=f"b3-failure-worker-{suffix}",
        )
        assert claimed.worker_execution_id is not None
        worker_execution = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == claimed.worker_execution_id))).scalar_one()
        worker_execution.status = "failed"
        worker_execution.error_code = "FIXTURE_FAILURE"
        worker_execution.error_message = "B3 failure fixture"
        await db.commit()

        finalized = await fail_delegation(
            db=db,
            tenant_id=delegation_row.tenant_id,
            delegation_id=delegation_row.id,
            worker_execution_id=claimed.worker_execution_id,
            error_code=worker_execution.error_code,
            error_message=worker_execution.error_message,
        )
        assert finalized.status == "failed"
        assert finalized.error_code == "FIXTURE_FAILURE"
        assert finalized.error_message == "B3 failure fixture"
        assert finalized.ended_at is not None
