"""Agent Delegation B4 timeout/cancel/parent semantics Real API 验收测试。

职责：通过真实 HTTP + PostgreSQL 验证 Delegation timeout/cancel 的终态边界，并证明父 Workflow Execution 不被子任务终态直接修改。
边界：复用 B2/B3 Fixture 与 Mock Provider，不重复实现 Delegation 创建或 Worker Runtime。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.infrastructure.db.session import SessionLocal
from app.models.agent_delegation import AgentDelegation
from app.models.core import utcnow_naive
from app.models.workflow_execution import WorkflowExecution
from app.services.agent_delegation.claim import claim_delegation
from app.services.workflow_worker import WorkflowWorker
from app.services.workflow_worker.runtime_entry import execute_claimed_execution
from tests.api_real.test_agent_delegation_bridge_api import _client, _create_delegation

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_b4_cancel_ends_delegation_without_changing_parent_execution() -> None:
    """验证取消只结束 Delegation，自身不把父 Workflow Execution 推入终态。"""
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        delegation_id, _, _, _, parent_execution_id = await _create_delegation(client, f"b4-cancel-{suffix}")
        response = client.post(f"/workflows/{parent_execution_id}/delegations/{delegation_id}/cancel")
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "cancelled"

        second = client.post(f"/workflows/{parent_execution_id}/delegations/{delegation_id}/cancel")
        assert second.status_code == 409, second.text

    async with SessionLocal() as db:
        delegation = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == uuid.UUID(delegation_id)))).scalar_one()
        parent = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == uuid.UUID(parent_execution_id)))).scalar_one()
        assert delegation.status == "cancelled"
        assert delegation.ended_at is not None
        assert parent.status == "pending"
        assert parent.ended_at is None


@pytest.mark.asyncio
async def test_b4_timeout_closes_child_without_terminalizing_parent() -> None:
    """验证已到期 Delegation 在 Worker Runtime 中进入 timed_out，父 Execution 保持非终态。

    本场景只验证 Claim 后的 timeout 分支。Claim 使用 `commit=False`，使 pending → running、Worker
    Execution、Frontier 与 timeout_at 写入保持在同一事务；提交前后台 Worker 无法观察到 running Claim，
    从而消除真实多 Worker 环境中的 pending → running 竞争窗口。
    """
    suffix = uuid.uuid4().hex[:10]
    with _client() as client:
        delegation_id, _, _, _, parent_execution_id = await _create_delegation(client, f"b4-timeout-{suffix}")

    async with SessionLocal() as db:
        delegation_uuid = uuid.UUID(delegation_id)
        delegation = (
            await db.execute(
                select(AgentDelegation)
                .where(AgentDelegation.id == delegation_uuid)
                .with_for_update()
            )
        ).scalar_one()
        claimed = await claim_delegation(
            db=db,
            tenant_id=delegation.tenant_id,
            delegation_id=delegation.id,
            worker_owner=f"b4-timeout-worker-{suffix}",
            commit=False,
        )
        assert claimed.worker_execution_id is not None
        delegation.timeout_at = utcnow_naive()
        await db.commit()
        worker_execution_id = claimed.worker_execution_id
        tenant_id = delegation.tenant_id

    worker = WorkflowWorker(lease_seconds=60)
    worker.owner = f"b4-timeout-worker-{suffix}"
    if not hasattr(worker, "_renew_with_abort_signal"):
        worker._renew_with_abort_signal = worker._renew_lease_once

    with pytest.raises(RuntimeError, match="Delegation 超过治理 timeout_seconds"):
        await execute_claimed_execution(worker, worker_execution_id)

    async with SessionLocal() as db:
        persisted = (await db.execute(select(AgentDelegation).where(AgentDelegation.id == delegation_uuid))).scalar_one()
        child = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == worker_execution_id))).scalar_one()
        parent = (await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == uuid.UUID(parent_execution_id)))).scalar_one()
        assert persisted.tenant_id == tenant_id
        assert persisted.status == "timed_out"
        assert persisted.error_code == "DELEGATION_TIMEOUT"
        assert persisted.ended_at is not None
        assert child.status == "cancelled"
        assert parent.status == "pending"
        assert parent.ended_at is None
