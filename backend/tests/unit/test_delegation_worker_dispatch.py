"""Durable Frontier Worker 的 Delegation dispatch 单元契约。

职责：验证默认 Worker 在没有普通 Frontier 时会发现 pending Delegation，并继续走同一 Frontier dispatch 入口。
边界：不复制数据库 Claim/Runtime 实现；只验证 dispatch 编排边界。
关键依赖：DurableFrontierWorkflowWorker、pytest asyncio。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow_worker.frontier_runtime import DurableFrontierWorkflowWorker


@pytest.mark.asyncio
async def test_dispatch_once_claims_pending_delegation_when_no_frontier(monkeypatch) -> None:
    """验证没有普通 Frontier 时，Worker 会先 Claim Delegation 再消费新建 Frontier。"""
    worker = DurableFrontierWorkflowWorker(concurrency=1, lease_seconds=60)
    frontier = SimpleNamespace(id=uuid4(), attempt=1, execution_id=uuid4(), tenant_id=uuid4())
    calls: list[str] = []

    async def claim_frontier():
        calls.append("frontier")
        if calls.count("frontier") == 1:
            return None
        return frontier

    async def claim_delegation():
        calls.append("delegation")
        return True

    async def execute_claimed(frontier_item):
        calls.append("execute")
        assert frontier_item is frontier

    monkeypatch.setattr(worker, "claim_one_frontier", claim_frontier)
    monkeypatch.setattr(worker, "claim_one_pending_delegation", claim_delegation)
    monkeypatch.setattr(worker, "execute_frontier", execute_claimed)

    assert await worker.dispatch_once() == 1
    assert calls == ["frontier", "delegation", "frontier", "execute"]
