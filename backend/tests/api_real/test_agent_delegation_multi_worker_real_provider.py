"""Agent Delegation 多 Worker 真实 Provider Real API 验收。

职责：通过真实 HTTP + PostgreSQL 创建真实 Provider/Profile，并让多个独立 Worker 实例竞争消费 Delegation Durable Frontier，验证真实 Provider 调用位于统一 Runtime Governance 链路。
边界：不实现 Provider、Worker 或 Delegation 第二套 Runtime；Provider endpoint、model 与凭据只从未提交运行环境读取。
关键依赖：真实 Backend HTTP、PostgreSQL、已配置 OpenAI-compatible/兼容 Provider、Durable Frontier Worker。
"""

from __future__ import annotations

import asyncio
import os
import uuid

import httpx
import pytest
from sqlalchemy import select

from app.infrastructure.db.session import SessionLocal
from app.models.agent_delegation import AgentDelegation
from app.models.core import AgentVersion, User
from app.models.model_provider import ModelProfile, ModelProvider
from app.models.organization import Organization
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.services.workflow_worker import WorkflowWorker
from tests.api_real.test_agent_delegation_bridge_api import _publish_agent

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    """创建带自动化测试 Token 的真实 HTTP 客户端。"""
    if not TOKEN:
        pytest.skip("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=60.0)


def _required_provider_setting(name: str) -> str:
    """读取真实 Provider 验收必需配置，不允许测试回退到 Mock Provider。"""
    value = os.getenv(name, "").strip()
    if not value:
        pytest.skip(f"{name} is required for real Provider validation")
    return value


async def _bind_real_provider_profile(target_version_id: uuid.UUID, suffix: str) -> uuid.UUID:
    """在 Delegation 创建前持久化真实 Provider/Profile，使 Worker Claim 后立即具备完整运行依赖。"""
    endpoint = _required_provider_setting("DELEGATION_REAL_PROVIDER_ENDPOINT")
    model_name = _required_provider_setting("DELEGATION_REAL_PROVIDER_MODEL")
    provider_type = os.getenv("DELEGATION_REAL_PROVIDER_TYPE", "openai-compatible").strip().lower()
    if provider_type not in {"openai-compatible", "ollama"}:
        raise AssertionError("DELEGATION_REAL_PROVIDER_TYPE 必须为 openai-compatible 或 ollama")
    credential_ref = os.getenv("DELEGATION_REAL_PROVIDER_API_KEY_ENV", "").strip() or None
    if credential_ref and not os.getenv(credential_ref):
        pytest.skip(f"{credential_ref} is required for real Provider validation")

    async with SessionLocal() as db:
        target_version = (
            await db.execute(select(AgentVersion).where(AgentVersion.id == target_version_id))
        ).scalar_one()
        target_agent = (
            await db.execute(select(Organization, User).join(User, User.tenant_id == Organization.tenant_id).where(User.id == target_agent.owner_id))
        ).first()
        if target_agent is None:
            raise AssertionError("Target Agent owner Organization 不存在")
        organization = target_agent[0]
        provider = ModelProvider(
            organization_id=organization.id,
            name=f"phase-28-real-provider-{suffix}",
            provider_type=provider_type,
            provider_name=f"phase-28-real-{suffix}",
            endpoint=endpoint,
            credential_ref=credential_ref,
            enabled=True,
            metadata_json={"purpose": "phase-2.8-real-provider-multi-worker"},
        )
        db.add(provider)
        await db.flush()
        profile = ModelProfile(
            provider_id=provider.id,
            name=f"phase-28-real-profile-{suffix}",
            model_type="chat",
            model_name=model_name,
            capabilities={},
            parameters={"timeout_seconds": 60},
            enabled=True,
            is_default=False,
        )
        db.add(profile)
        await db.flush()
        target_version.model_profile_id = profile.id
        await db.commit()
        return profile.id


async def _create_real_provider_delegation(client: httpx.Client, suffix: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """创建绑定真实 Provider/Profile 的 Delegation Fixture。"""
    orchestrator_id, _ = _publish_agent(client, f"phase-28-real-orchestrator-{suffix}")
    target_agent_id, target_version_id = _publish_agent(client, f"phase-28-real-worker-{suffix}")
    workflow = client.post(
        "/workflows",
        json={"name": f"phase-28-real-{suffix}", "description": "Delegation real Provider multi-worker fixture"},
    )
    assert workflow.status_code == 201, workflow.text
    workflow_id = workflow.json()["id"]
    version = client.post(
        f"/workflows/{workflow_id}/versions",
        json={
            "definition": {
                "config": {"timeout_ms": 120000},
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
        json={"input_data": {"fixture": "real-provider-multi-worker"}},
    )
    assert execution.status_code == 201, execution.text
    execution_id = uuid.UUID(execution.json()["id"])
    profile_id = await _bind_real_provider_profile(uuid.UUID(target_version_id), suffix)
    delegation = client.post(
        f"/workflows/{execution_id}/delegations",
        json={
            "target_agent_version_id": target_version_id,
            "delegation_key": f"real-provider-{suffix}",
            "input_data": {"prompt": "Reply with a short confirmation that the delegated task was executed."},
            "selected_context_refs": [],
            "allowed_tools": [],
            "timeout_seconds": 90,
        },
    )
    assert delegation.status_code == 201, delegation.text
    delegation_id = uuid.UUID(delegation.json()["id"])
    assert uuid.UUID(delegation.json()["model_profile_id"]) == profile_id
    return delegation_id, uuid.UUID(target_agent_id), profile_id


async def _wait_terminal(delegation_id: uuid.UUID, timeout_seconds: float = 120.0) -> AgentDelegation:
    """等待 Delegation 终态；超时输出 Worker durable ownership 事实。"""
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        async with SessionLocal() as db:
            delegation = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_id))).scalar_one()
            if delegation.status in {"completed", "failed", "cancelled", "timed_out"}:
                return delegation
            execution = None
            frontier = None
            if delegation.worker_execution_id is not None:
                execution = (
                    await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == delegation.worker_execution_id))
                ).scalar_one_or_none()
                frontier = (
                    await db.execute(
                        select(WorkflowFrontier)
                        .where(WorkflowFrontier.execution_id == delegation.worker_execution_id)
                        .order_by(WorkflowFrontier.created_at.asc(), WorkflowFrontier.id.asc())
                        .limit(1)
                    )
                ).scalar_one_or_none()
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError(
                f"真实 Provider Delegation 未在 {timeout_seconds}s 内完成："
                f" delegation={delegation.status}, "
                f"execution={None if execution is None else {'status': execution.status, 'worker_owner': execution.worker_owner}}, "
                f"frontier={None if frontier is None else {'status': frontier.status, 'worker_owner': frontier.worker_owner, 'attempt': frontier.attempt}}"
            )
        await asyncio.sleep(0.25)


@pytest.mark.asyncio
async def test_multiple_workers_execute_delegation_through_real_provider() -> None:
    """验证两个独立 Worker 实例竞争多个 Delegation 时，最终全部通过同一真实 Provider 完成。"""
    suffix = uuid.uuid4().hex[:10]
    fixtures: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]] = []

    with _client() as client:
        for index in range(2):
            fixtures.append(await _create_real_provider_delegation(client, f"{suffix}-{index}"))

    worker_a = WorkflowWorker(concurrency=1, lease_seconds=60)
    worker_b = WorkflowWorker(concurrency=1, lease_seconds=60)
    worker_a.owner = f"real-provider-worker-a-{suffix}"
    worker_b.owner = f"real-provider-worker-b-{suffix}"

    first_round = await asyncio.gather(
        worker_a._claim_pending_delegation_frontier(),
        worker_b._claim_pending_delegation_frontier(),
    )
    pairs = [(worker, frontier) for worker, frontier in zip((worker_a, worker_b), first_round) if frontier is not None]
    if pairs:
        await asyncio.gather(*(worker.execute_frontier(frontier) for worker, frontier in pairs))

    deadline = asyncio.get_running_loop().time() + 120.0
    while asyncio.get_running_loop().time() < deadline:
        async with SessionLocal() as db:
            statuses = {
                row[0]: row[1]
                for row in (
                    await db.execute(
                        select(AgentDelegation.id, AgentDelegation.status).where(
                            AgentDelegation.id.in_([item[0] for item in fixtures])
                        )
                    )
                ).all()
            }
        if len(statuses) == len(fixtures) and all(status == "completed" for status in statuses.values()):
            break
        worker = worker_a if len(statuses) % 2 == 0 else worker_b
        frontier = await worker._claim_pending_delegation_frontier()
        if frontier is not None:
            await worker.execute_frontier(frontier)
        await asyncio.sleep(0)

    for delegation_id, target_agent_id, profile_id in fixtures:
        persisted = await _wait_terminal(delegation_id)
        assert persisted.status == "completed"
        assert persisted.model_profile_id == profile_id
        async with SessionLocal() as db:
            execution = (
                await db.execute(
                    select(WorkflowExecution).where(
                        WorkflowExecution.id == persisted.worker_execution_id,
                        WorkflowExecution.tenant_id == persisted.tenant_id,
                    )
                )
            ).scalar_one()
            frontier = (
                await db.execute(
                    select(WorkflowFrontier).where(
                        WorkflowFrontier.execution_id == execution.id,
                        WorkflowFrontier.tenant_id == persisted.tenant_id,
                    )
                )
            ).scalar_one()
            profile = (await db.execute(select(ModelProfile).where(ModelProfile.id == profile_id))).scalar_one()
            provider = (await db.execute(select(ModelProvider).where(ModelProvider.id == profile.provider_id))).scalar_one()
            assert provider.provider_type in {"openai-compatible", "ollama"}
            assert provider.enabled is True
            assert profile.enabled is True
            assert execution.status == "completed"
            assert execution.output_data
            assert execution.output_data["agent_id"] == str(target_agent_id)
            assert execution.output_data["model_id"] == profile.model_name
            assert frontier.status == "completed"
            assert frontier.worker_owner is None
            assert execution.worker_owner is None
