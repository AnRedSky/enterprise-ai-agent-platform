"""Agent Delegation 多 Worker Runtime Real API 验收测试。

职责：通过真实 HTTP + PostgreSQL 驱动多个独立 Worker 实例消费 Delegation Durable Frontier，验证 Claim、Frontier、WorkflowExecution 与 Delegation 终态形成完整闭环。
边界：不复制 Worker Runtime；只装配真实测试数据并调用现有 WorkflowWorker dispatch 入口。
关键依赖：真实 Backend HTTP、PostgreSQL、Mock Model Provider、Durable Frontier Worker。
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
from app.models.core import AuditLog
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.services.workflow_worker import WorkflowWorker
from tests.api_real.test_agent_delegation_bridge_api import _bind_deterministic_mock_profile, _create_delegation

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
pytestmark = pytest.mark.real_api


def _client() -> httpx.Client:
    """创建带自动化测试 Token 的真实 HTTP 客户端。

    Returns:
        httpx.Client: 携带真实访问令牌的 HTTP 客户端。

    Raises:
        pytest.skip: 未提供 ACCESS_TOKEN 时跳过真实 API 场景。
    """
    if not TOKEN:
        pytest.skip("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30.0)


@pytest.mark.asyncio
async def test_delegation_is_consumed_by_multiple_worker_instances_through_durable_frontier() -> None:
    """验证多个 Worker 实例通过 Durable Frontier 消费 Delegation，且每个 Delegation 只形成一个执行事实。"""
    suffix = uuid.uuid4().hex[:10]
    fixtures: list[tuple[str, str]] = []

    with _client() as client:
        for index in range(4):
            delegation_id, _, _, _, parent_execution_id = _create_delegation(
                client,
                f"b6-multi-worker-{suffix}-{index}",
            )
            fixtures.append((delegation_id, parent_execution_id))

    async with SessionLocal() as db:
        for index, (delegation_id, _) in enumerate(fixtures):
            await _bind_deterministic_mock_profile(
                db,
                uuid.UUID(delegation_id),
                f"{suffix}-{index}",
            )

    worker_a = WorkflowWorker(concurrency=1, lease_seconds=60)
    worker_b = WorkflowWorker(concurrency=1, lease_seconds=60)
    worker_a.owner = f"b6-worker-a-{suffix}"
    worker_b.owner = f"b6-worker-b-{suffix}"

    # 多 Worker 部署下允许其他已运行 Worker 同时消费 durable work item，因此不再把“本地两个 Worker 的 dispatch 返回值之和”等同于 Delegation 总消费数。
    # 真正的一次性消费事实由 Delegation Claim AuditLog + worker_execution_id + Frontier attempt 共同证明。
    dispatch_rounds = []
    for _ in range(2):
        dispatch_rounds.append(
            await asyncio.gather(
                worker_a.dispatch_once(),
                worker_b.dispatch_once(),
            )
        )

    async with SessionLocal() as db:
        delegation_rows = (
            await db.execute(
                select(AgentDelegation).where(
                    AgentDelegation.id.in_([uuid.UUID(item[0]) for item in fixtures])
                )
            )
        ).scalars().all()
        assert len(delegation_rows) == len(fixtures)

        parent_ids = [uuid.UUID(item[1]) for item in fixtures]
        claim_events = (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.workflow_execution_id.in_(parent_ids),
                    AuditLog.action == "workflow.delegation.claimed",
                    AuditLog.resource_type == "agent_delegation",
                    AuditLog.resource_id.in_([item[0] for item in fixtures]),
                )
            )
        ).scalars().all()
        assert len(claim_events) == len(fixtures)
        assert len({event.resource_id for event in claim_events}) == len(fixtures)
        claim_owners = {
            str((event.metadata_json or {}).get("worker_owner"))
            for event in claim_events
            if (event.metadata_json or {}).get("worker_owner")
        }
        assert worker_a.owner in claim_owners
        assert worker_b.owner in claim_owners

        for delegation_id, parent_execution_id in fixtures:
            delegation = next(item for item in delegation_rows if item.id == uuid.UUID(delegation_id))
            assert delegation.status == "completed"
            assert delegation.worker_execution_id is not None

            execution = (
                await db.execute(
                    select(WorkflowExecution).where(
                        WorkflowExecution.id == delegation.worker_execution_id,
                        WorkflowExecution.tenant_id == delegation.tenant_id,
                    )
                )
            ).scalar_one()
            assert execution.status == "completed"
            # Terminalization 会原子释放 Execution lease；owner 在 running 阶段由 Frontier/Execution fencing 保证一致。
            assert execution.worker_owner is None
            assert execution.output_data is not None

            frontier = (
                await db.execute(
                    select(WorkflowFrontier).where(
                        WorkflowFrontier.execution_id == execution.id,
                        WorkflowFrontier.tenant_id == delegation.tenant_id,
                    )
                )
            ).scalar_one()
            assert frontier.status == "completed"
            # Frontier terminalization 同样释放 lease；attempt=1 证明该 Delegation 没有被第二个 Worker 重复消费。
            assert frontier.worker_owner is None
            assert frontier.node_ids == ["delegation.target"]
            assert frontier.attempt == 1

            parent = (
                await db.execute(
                    select(WorkflowExecution).where(
                        WorkflowExecution.id == uuid.UUID(parent_execution_id),
                        WorkflowExecution.tenant_id == delegation.tenant_id,
                    )
                )
            ).scalar_one()
            assert parent.status == "pending"

        worker_execution_ids = [delegation.worker_execution_id for delegation in delegation_rows]
        assert len(worker_execution_ids) == len(set(worker_execution_ids))
