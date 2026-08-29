"""Durable Frontier Worker 的 Delegation dispatch 单元契约。

职责：验证默认 Worker 在没有普通 Frontier 时会发现 pending Delegation，并直接消费 Claim 返回的 Frontier。
边界：不复制数据库 Claim/Runtime 实现；只验证 dispatch 编排边界。
关键依赖：DurableFrontierWorkflowWorker、pytest asyncio。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow_worker.frontier_runtime import DurableFrontierWorkflowWorker


@pytest.mark.asyncio
async def test_dispatch_once_claims_pending_delegation_frontier_without_rescan(monkeypatch) -> None:
    """验证没有普通 Frontier 时，Worker 直接消费 Delegation Claim 返回的 Frontier，不重复全局扫描。"""
    worker = DurableFrontierWorkflowWorker(concurrency=1, lease_seconds=60)
    frontier = SimpleNamespace(id=uuid4(), attempt=1, execution_id=uuid4(), tenant_id=uuid4())
    calls: list[str] = []

    async def claim_frontier():
        calls.append("frontier")
        return None

    async def claim_delegation_frontier():
        calls.append("delegation")
        return frontier

    async def execute_claimed(frontier_item):
        calls.append("execute")
        assert frontier_item is frontier

    monkeypatch.setattr(worker, "claim_one_frontier", claim_frontier)
    monkeypatch.setattr(worker, "_claim_pending_delegation_frontier", claim_delegation_frontier)
    monkeypatch.setattr(worker, "execute_frontier", execute_claimed)

    assert await worker.dispatch_once() == 1
    assert calls == ["frontier", "delegation", "execute"]
