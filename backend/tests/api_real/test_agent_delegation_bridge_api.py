"""Agent Delegation B2/B3 Worker Runtime Real API 验收测试。

职责：通过真实 HTTP + PostgreSQL 验证 B1 Claim、B2 target Agent Runtime 与 B3 Delegation generation fencing。
边界：不验证 B4 timeout/cancel/parent semantics。
关键依赖：真实 Backend HTTP、PostgreSQL、Mock Model Provider、Workflow Worker Runtime。
"""

from __future__ import annotations

import asyncio
import os
import uuid

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.infrastructure.db.session import SessionLocal
from app.models.agent_delegation import AgentDelegation
from app.models.core import Agent, AgentVersion, User
from app.models.model_provider import ModelProfile, ModelProvider
from app.models.organization import Organization
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.services.agent_delegation.claim import claim_delegation
from app.services.agent_delegation.completion import complete_delegation, fail_delegation
from app.services.workflow_worker import WorkflowWorker

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
            "description": "Phase 2.8 Delegation Runtime fixture",
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


async def _prepare_target_model_profile(target_version_id: uuid.UUID, suffix: str, *, model_name: str = "mock-model") -> uuid.UUID:
    """在 Delegation 创建前提交 Target Agent 的完整 Mock Provider/Profile 链路。"""
    async with SessionLocal() as db:
        target_version = (await db.execute(select(AgentVersion).where(AgentVersion.id == target_version_id))).scalar_one()
        target_agent = (await db.execute(select(Agent).where(Agent.id == target_version.agent_id))).scalar_one()
        owner = (await db.execute(select(User).where(User.id == target_agent.owner_id))).scalar_one()
        organization = (await db.execute(select(Organization).where(Organization.tenant_id == owner.tenant_id))).scalar_one()

        provider = ModelProvider(
            organization_id=organization.id,
            name=f"phase-28-mock-provider-{suffix}",
            provider_type="mock",
            provider_name="phase-28-real-gate",
            enabled=True,
            metadata_json={"purpose": "phase-2.8-real-gate"},
        )
        db.add(provider)
        await db.flush()
        profile = ModelProfile(
            provider_id=provider.id,
            name=f"phase-28-mock-profile-{suffix}",
            model_type="chat",
            model_name=model_name,
            capabilities={},
            parameters={},
            enabled=True,
            is_default=False,
        )
        db.add(profile)
        await db.flush()
        target_version.model_profile_id = profile.id
        await db.commit()
        return profile.id


async def _create_delegation(client: httpx.Client, suffix: str, *, model_name: str = "mock-model") -> tuple[str, str, str, str, str]:
    """创建真实 Workflow/Execution/Delegation Fixture，并在 Delegation 可见前完成 Provider 装配。"""
    orchestrator_id, _ = _publish_agent(client, f"phase-28-b2-orchestrator-{suffix}")
    target_agent_id, target_version_id = _publish_agent(client, f"phase-28-b2-worker-{suffix}")
    workflow = client.post("/workflows", json={"name": f"phase-28-b2-{suffix}", "description": "Delegation Runtime fixture"})
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
    execution = client.post(f"/workflows/{workflow_id}/executions", json={"input_data": {"fixture": "b2-bridge"}})
    assert execution.status_code == 201, execution.text
    execution_id = execution.json()["id"]
    profile_id = await _prepare_target_model_profile(uuid.UUID(target_version_id), suffix, model_name=model_name)
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
    response = delegation.json()
    assert response["model_profile_id"] == str(profile_id)
    return response["id"], target_agent_id, target_version_id, workflow_version_id, execution_id


async def _wait_for_terminal_delegation(delegation_id: uuid.UUID, timeout_seconds: float = 30.0) -> AgentDelegation:
    """等待任一合法 Worker 完成竞争中的 Delegation。"""
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        async with SessionLocal() as db:
            delegation = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_id))).scalar_one()
            if delegation.status in {"completed", "failed", "cancelled", "timed_out"}:
                return delegation
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError(f"Delegation {delegation_id} did not reach a terminal state within {timeout_seconds}s")
        await asyncio.sleep(0.2)


async def _claim_or_observe_running(db, delegation_id: uuid.UUID, tenant_id, worker_owner: str) -> AgentDelegation:
    """Claim pending Delegation；若后台 Worker 已合法抢占，则读取 durable running 状态。"""
    current = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_id))).scalar_one()
    if current.status == "pending":
        try:
            return await claim_delegation(db=db, tenant_id=tenant_id, delegation_id=delegation_id, worker_owner=worker_owner)
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
            await db.rollback()
        except IntegrityError:
            # 并发 Worker 可能已经提交相同 delegation:{id} Execution；回滚后必须重新读取 durable 状态。
            await db.rollback()
    current = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_id))).scalar_one()
    if current.status != "running":
        raise AssertionError(f"Delegation 必须处于 pending/running，实际为 {current.status}")
    assert current.worker_execution_id is not None
    return current


@pytest.mark.asyncio
async def test_b2_worker_execution_bridge_runs_target_agent_version():
    """验证 Claim 后正式 Durable Frontier Worker 执行 target Agent，并完成 Execution/Frontier/Delegation。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        delegation_id, target_agent_id, target_version_id, workflow_version_id, _ = await _create_delegation(client, suffix)

    worker = WorkflowWorker(lease_seconds=60)
    worker.owner = f"b2-worker-{suffix}"
    delegation_uuid = uuid.UUID(delegation_id)

    async with SessionLocal() as db:
        delegation = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_uuid))).scalar_one()
        delegation_status = delegation.status
        delegation_tenant_id = delegation.tenant_id
        if delegation_status == "pending":
            claimed = await claim_delegation(db=db, tenant_id=delegation_tenant_id, delegation_id=delegation_uuid, worker_owner=worker.owner, commit=False)
            worker_execution_id = claimed.worker_execution_id
            assert worker_execution_id is not None
            await db.commit()
        else:
            assert delegation_status == "running"
            worker_execution_id = delegation.worker_execution_id
            assert worker_execution_id is not None

    async with SessionLocal() as db:
        execution = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == worker_execution_id))).scalar_one()
        execution_status = execution.status
        execution_owner = execution.worker_owner
        execution_id_value = execution.id
        await db.rollback()
        if execution_status in {"completed", "failed", "cancelled"}:
            persisted = await _wait_for_terminal_delegation(delegation_uuid)
        elif execution_owner == worker.owner:
            frontier = await worker._claim_pending_delegation_frontier()
            if frontier is not None:
                await worker.execute_frontier(frontier)
            # Frontier 可能已被其他 Worker 消费；只要 durable generation 合法并最终收敛即可。
            persisted = await _wait_for_terminal_delegation(delegation_uuid)
        else:
            persisted = await _wait_for_terminal_delegation(delegation_uuid)

    assert persisted.status == "completed"
    async with SessionLocal() as db:
        persisted = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_uuid))).scalar_one()
        worker_execution = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == persisted.worker_execution_id))).scalar_one()
        frontier = (await db.execute(select(WorkflowFrontier).where(WorkflowFrontier.execution_id == worker_execution.id))).scalar_one()
        target_version = (await db.execute(select(AgentVersion).where(AgentVersion.id == uuid.UUID(target_version_id)))).scalar_one()
        profile = (await db.execute(select(ModelProfile).where(ModelProfile.id == persisted.model_profile_id))).scalar_one()
        provider = (await db.execute(select(ModelProvider).where(ModelProvider.id == profile.provider_id))).scalar_one()
        assert persisted.status == "completed"
        assert worker_execution.status == "completed"
        assert frontier.status == "completed"
        assert frontier.worker_owner is None
        assert worker_execution.output_data["agent_id"] == target_agent_id
        assert worker_execution.output_data["agent_version"] is not None
        assert target_version.model_profile_id == persisted.model_profile_id
        assert provider.provider_type == "mock"
        assert profile.model_name == "mock-model"
        assert worker_execution.workflow_version_id == uuid.UUID(workflow_version_id)
        assert worker_execution.tenant_id == persisted.tenant_id


@pytest.mark.asyncio
async def test_b3_stale_worker_generation_cannot_complete_delegation():
    """验证旧 Worker generation 不能提前收敛当前 Delegation。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        delegation_id, _, _, _, _ = await _create_delegation(client, f"b3-{suffix}")
    async with SessionLocal() as db:
        delegation = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == uuid.UUID(delegation_id)))).scalar_one()
        delegation_id_value = delegation.id
        tenant_id_value = delegation.tenant_id
        claimed = await _claim_or_observe_running(db, delegation_id_value, tenant_id_value, f"b3-worker-{suffix}")
        with pytest.raises(HTTPException) as exc_info:
            await complete_delegation(db=db, tenant_id=tenant_id_value, delegation_id=delegation_id_value, worker_execution_id=uuid.uuid4())
        assert exc_info.value.status_code == 409
        await db.rollback()
        persisted = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_id_value))).scalar_one()
        assert persisted.status == "running"
        assert persisted.worker_execution_id == claimed.worker_execution_id


@pytest.mark.asyncio
async def test_b3_failed_worker_execution_closes_delegation():
    """验证 Worker Execution 已持久化失败后，当前 generation 能收敛 Delegation failed。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        delegation_id, _, _, _, _ = await _create_delegation(client, f"b3-failure-{suffix}", model_name="mock-http-503")
    delegation_uuid = uuid.UUID(delegation_id)
    worker_owner = f"b3-failure-worker-{suffix}"
    deadline = asyncio.get_running_loop().time() + 30.0
    while True:
        async with SessionLocal() as db:
            delegation = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_uuid))).scalar_one()
            delegation_status = delegation.status
            delegation_tenant_id = delegation.tenant_id
            delegation_id_value = delegation.id
            if delegation_status in {"completed", "failed", "cancelled", "timed_out"}:
                persisted_status = delegation_status
                break
            if delegation_status == "pending":
                try:
                    claimed = await claim_delegation(
                        db=db,
                        tenant_id=delegation_tenant_id,
                        delegation_id=delegation_id_value,
                        worker_owner=worker_owner,
                    )
                except (HTTPException, IntegrityError):
                    await db.rollback()
                    continue
                execution_id = claimed.worker_execution_id
                assert execution_id is not None
            else:
                execution_id = delegation.worker_execution_id
                assert execution_id is not None

            execution = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))).scalar_one()
            if execution.worker_owner != worker_owner:
                await db.rollback()
                if asyncio.get_running_loop().time() >= deadline:
                    break
                await asyncio.sleep(0.2)
                continue
            execution.status = "failed"
            execution.error_code = "FIXTURE_FAILURE"
            execution.error_message = "B3 failure fixture"
            await db.commit()
            finalized = await fail_delegation(
                db=db,
                tenant_id=delegation_tenant_id,
                delegation_id=delegation_id_value,
                worker_execution_id=execution.id,
                error_code="FIXTURE_FAILURE",
                error_message="B3 failure fixture",
            )
            persisted_status = finalized.status
            break
        if asyncio.get_running_loop().time() >= deadline:
            break
        await asyncio.sleep(0.2)

    if persisted_status != "failed":
        persisted = await _wait_for_terminal_delegation(delegation_uuid)
    else:
        persisted = await _wait_for_terminal_delegation(delegation_uuid)
    assert persisted.status == "failed"
    assert persisted.error_code is not None
    assert persisted.ended_at is not None
