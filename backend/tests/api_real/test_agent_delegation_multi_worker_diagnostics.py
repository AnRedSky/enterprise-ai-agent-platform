"""Agent Delegation 多 Worker Durable Runtime 事实诊断。

职责：复现 B6 多 Worker Delegation Claim/Execute 边界，并在未收敛时直接输出真实 PostgreSQL durable facts。
边界：不复制 Runtime；只调用正式 Worker Claim/Execute 入口，诊断读取不修改业务状态。
关键依赖：真实 PostgreSQL、Mock Model Provider、WorkflowWorker。
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import select

from app.infrastructure.db.session import SessionLocal
from app.models.agent_delegation import AgentDelegation
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.services.workflow_worker import WorkflowWorker
from tests.api_real.test_agent_delegation_bridge_api import _bind_deterministic_mock_profile, _create_delegation
from tests.api_real.test_agent_delegation_multi_worker_api import _client

pytestmark = pytest.mark.real_api


async def _dump_facts(ids: list[uuid.UUID]) -> str:
    """读取本次 Delegation 的完整 durable 链路事实。

    Args:
        ids: 本次诊断创建的 Delegation 标识。

    Returns:
        str: Delegation、Worker Execution、Frontier 的状态、ownership、lease 与错误事实。
    """
    async with SessionLocal() as db:
        rows = (await db.execute(select(AgentDelegation).where(AgentDelegation.id.in_(ids)))).scalars().all()
        lines: list[str] = []
        for item in sorted(rows, key=lambda row: str(row.id)):
            execution = None
            frontier = None
            if item.worker_execution_id:
                execution = (await db.execute(select(WorkflowExecution).where(
                    WorkflowExecution.id == item.worker_execution_id,
                    WorkflowExecution.tenant_id == item.tenant_id,
                ))).scalar_one_or_none()
                if execution:
                    frontier = (await db.execute(select(WorkflowFrontier).where(
                        WorkflowFrontier.execution_id == execution.id,
                        WorkflowFrontier.tenant_id == execution.tenant_id,
                    ).order_by(WorkflowFrontier.created_at.asc(), WorkflowFrontier.id.asc()))).scalars().first()
            lines.append(
                f"delegation={item.id} status={item.status} worker_execution_id={item.worker_execution_id} "
                f"error={item.error_code!r}:{item.error_message!r} "
                f"| execution={getattr(execution, 'id', None)} status={getattr(execution, 'status', None)} "
                f"owner={getattr(execution, 'worker_owner', None)!r} attempt={getattr(execution, 'worker_attempt', None)} "
                f"lease={getattr(execution, 'worker_lease_expires_at', None)} "
                f"error={getattr(execution, 'error_code', None)!r}:{getattr(execution, 'error_message', None)!r} "
                f"| frontier={getattr(frontier, 'id', None)} status={getattr(frontier, 'status', None)} "
                f"owner={getattr(frontier, 'worker_owner', None)!r} attempt={getattr(frontier, 'attempt', None)} "
                f"lease={getattr(frontier, 'worker_lease_expires_at', None)} "
                f"error={getattr(frontier, 'error_code', None)!r}:{getattr(frontier, 'error_message', None)!r}"
            )
        return "\n".join(lines)


@pytest.mark.asyncio
async def test_b6_multi_worker_diagnostic_dump_on_nonterminal_runtime() -> None:
    """复现 B6 多 Worker 消费并在固定边界后输出 durable state，不通过延长 timeout 隐藏问题。"""
    suffix = uuid.uuid4().hex[:10]
    ids: list[uuid.UUID] = []
    with _client() as client:
        for index in range(4):
            delegation_id, _, _, _, _ = _create_delegation(client, f"b6-diagnostic-{suffix}-{index}")
            ids.append(uuid.UUID(delegation_id))

    async with SessionLocal() as db:
        for index, delegation_id in enumerate(ids):
            await _bind_deterministic_mock_profile(db, delegation_id, f"{suffix}-{index}")

    worker_a = WorkflowWorker(concurrency=1, lease_seconds=60)
    worker_b = WorkflowWorker(concurrency=1, lease_seconds=60)
    worker_a.owner = f"b6-diagnostic-a-{suffix}"
    worker_b.owner = f"b6-diagnostic-b-{suffix}"

    for _ in range(2):
        frontiers = await asyncio.gather(
            worker_a._claim_pending_delegation_frontier(),
            worker_b._claim_pending_delegation_frontier(),
        )
        pairs = [(worker, frontier) for worker, frontier in zip((worker_a, worker_b), frontiers) if frontier is not None]
        if pairs:
            await asyncio.gather(*(worker.execute_frontier(frontier) for worker, frontier in pairs))

    facts = await _dump_facts(ids)
    print("\n===== B6 durable runtime diagnostic facts =====\n" + facts + "\n===== end diagnostic facts =====")
    async with SessionLocal() as db:
        statuses = (await db.execute(select(AgentDelegation.status).where(AgentDelegation.id.in_(ids)))).scalars().all()
    assert all(status in {"completed", "failed", "cancelled"} for status in statuses), facts
