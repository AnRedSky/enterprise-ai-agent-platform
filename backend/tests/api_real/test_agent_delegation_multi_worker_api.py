"""Agent Delegation 多 Worker Runtime Real API 验收测试。

职责：通过真实 HTTP + PostgreSQL 驱动多个独立 Worker 实例消费 Delegation Durable Frontier，验证 Claim、Frontier、WorkflowExecution 与 Delegation 终态形成完整闭环。
边界：不复制 Worker Runtime；只装配真实测试数据并调用现有 Delegation Frontier Claim / Execute 入口。
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


async def _delegation_statuses(delegation_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """读取本次验收 Delegation 当前状态。"""
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(AgentDelegation.id, AgentDelegation.status).where(AgentDelegation.id.in_(delegation_ids))
            )
        ).all()
    return {delegation_id: status for delegation_id, status in rows}


async def _assert_delegations_terminal(delegation_ids: list[uuid.UUID]) -> None:
    """在有界 dispatch drain 结束后断言所有 Delegation 已进入终态，并输出实际状态。"""
    statuses = await _delegation_statuses(delegation_ids)
    terminal = {"completed", "failed", "cancelled"}
    if len(statuses) != len(delegation_ids) or not all(status in terminal for status in statuses.values()):
        actual = {str(item): status for item, status in statuses.items()}
        raise AssertionError(f"Durable Worker 未在有界 dispatch drain 窗口内完成 Delegation 集合：{actual}")


async def _dispatch_with_worker(worker: WorkflowWorker) -> WorkflowFrontier | None:
    """让指定 Worker Claim 并立即执行一个 Delegation Frontier。"""
    frontier = await worker._claim_pending_delegation_frontier()
    if frontier is None:
        return None
    await worker.execute_frontier(frontier)
    return frontier


@pytest.mark.asyncio
async def test_delegation_is_consumed_by_multiple_worker_instances_through_durable_frontier() -> None:
    """验证多个 Worker 实例通过 Delegation Durable Frontier 消费任务，且每个 Delegation 只形成一个执行事实。"""
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
    delegation_ids = [uuid.UUID(item[0]) for item in fixtures]

    # Gate 明确允许已有后台 Worker 并发执行；当前测试 Worker 不要求垄断全部 Claim ownership。
    deadline = asyncio.get_running_loop().time() + 10.0
    first_round = await asyncio.gather(
        worker_a._claim_pending_delegation_frontier(),
        worker_b._claim_pending_delegation_frontier(),
    )
    first_pairs = [
        (worker, frontier)
        for worker, frontier in zip((worker_a, worker_b), first_round)
        if frontier is not None
    ]
    if first_pairs:
        await asyncio.gather(*(worker.execute_frontier(frontier) for worker, frontier in first_pairs))

    turn = 0
    while asyncio.get_running_loop().time() < deadline:
        statuses = await _delegation_statuses(delegation_ids)
        if len(statuses) == len(delegation_ids) and all(
            status in {"completed", "failed", "cancelled"} for status in statuses.values()
        ):
            break
        worker = worker_a if turn % 2 == 0 else worker_b
        await _dispatch_with_worker(worker)
        turn += 1
        await asyncio.sleep(0)

    await _assert_delegations_terminal(delegation_ids)

    async with SessionLocal() as db:
        delegation_rows = (
            await db.execute(
                select(AgentDelegation).where(AgentDelegation.id.in_(delegation_ids))
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
        # 既有 Worker 可以合法参与 Claim，因此不再要求 worker_b 必须恰好获得一个任务。
        # 同时保留至少一个本测试 Worker 的 Claim 断言，确保本测试确实覆盖独立 Worker 实例入口。
        assert worker_a.owner in claim_owners or worker_b.owner in claim_owners
        assert len(claim_owners) >= 2

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
