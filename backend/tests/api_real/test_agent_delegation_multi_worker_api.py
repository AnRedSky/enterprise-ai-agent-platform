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


async def _wait_for_delegations_terminal(delegation_ids: list[uuid.UUID], timeout_seconds: float = 10.0) -> None:
    """等待本测试创建的 Delegation 全部进入终态，避免把异步 dispatch 返回点误判为执行完成。

    Args:
        delegation_ids: 本次验收创建的 Delegation 标识。
        timeout_seconds: 最长等待时间；超过后由最终断言输出实际状态。

    Returns:
        None。

    Raises:
        TimeoutError: Durable Worker 在限定时间内没有完成全部 Delegation。
    """
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        async with SessionLocal() as db:
            rows = (
                await db.execute(
                    select(AgentDelegation.status).where(AgentDelegation.id.in_(delegation_ids))
                )
            ).scalars().all()
        if len(rows) == len(delegation_ids) and all(status in {"completed", "failed", "cancelled"} for status in rows):
            return
        await asyncio.sleep(0.1)
    raise TimeoutError("Durable Worker 未在验收等待窗口内完成本次 Delegation 集合")


async def _delegation_statuses(delegation_ids: list[uuid.UUID]) -> list[str]:
    """读取本次验收 Delegation 状态，用于驱动有界的多 Worker dispatch drain。

    Args:
        delegation_ids: 本次验收创建的 Delegation 标识。

    Returns:
        list[str]: 按数据库返回顺序排列的 Delegation 当前状态。
    """
    async with SessionLocal() as db:
        return list(
            (
                await db.execute(
                    select(AgentDelegation.status).where(AgentDelegation.id.in_(delegation_ids))
                )
            ).scalars().all()
        )


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

    # 本验收同时存在父 Workflow 的普通 Frontier。若调用通用 claim_one_frontier()，Worker 可能合法地先消费父 Workflow，
    # 从而无法证明本轮正在验收的 Delegation 已被 Claim。这里直接调用正式 Delegation Frontier discovery 入口；该入口仍使用
    # 真实 PostgreSQL Claim、真实 Frontier lease 与真实 execute_frontier，不复制任何 Runtime 实现。
    #
    # Claim 内部会提交事务并释放候选行锁，因此两个 Worker 在并发竞争时可能合法地命中同一个候选快照，
    # 其中一个随后收到 409 并返回 None。固定执行两轮会把这种合法竞争误判成“只消费 2/4”。
    # 这里改为在有界窗口内持续 drain，直到本测试创建的 Delegation 全部进入终态；不延长业务 timeout，
    # 也不依赖后台 Scheduler，因此仍然只验证本次显式 Worker dispatch 边界。
    deadline = asyncio.get_running_loop().time() + 10.0
    delegation_ids = [uuid.UUID(item[0]) for item in fixtures]
    while asyncio.get_running_loop().time() < deadline:
        statuses = await _delegation_statuses(delegation_ids)
        if len(statuses) == len(delegation_ids) and all(
            status in {"completed", "failed", "cancelled"} for status in statuses
        ):
            break

        frontiers = await asyncio.gather(
            worker_a._claim_pending_delegation_frontier(),
            worker_b._claim_pending_delegation_frontier(),
        )
        pairs = [(worker, frontier) for worker, frontier in zip((worker_a, worker_b), frontiers) if frontier is not None]
        if pairs:
            await asyncio.gather(*(worker.execute_frontier(frontier) for worker, frontier in pairs))
        else:
            await asyncio.sleep(0.1)

    await _wait_for_delegations_terminal(delegation_ids)

    async with SessionLocal() as db:
        delegation_rows = (
            await db.execute(
                select(AgentDelegation).where(
                    AgentDelegation.id.in_(delegation_ids)
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
