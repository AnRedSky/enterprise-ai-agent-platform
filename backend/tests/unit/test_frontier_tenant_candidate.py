"""Durable Frontier tenant candidate 的单元测试。

验证 Worker 不会因为最早 Frontier 所属 Execution 被其他 Worker 的有效 lease 阻塞，
而跳过其他 tenant 中当前可安全 Claim 的 Frontier。
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow_worker.frontier_runtime import DurableFrontierWorkflowWorker


@pytest.mark.asyncio
async def test_frontier_tenant_candidate_selects_only_execution_eligible_work() -> None:
    worker = object.__new__(DurableFrontierWorkflowWorker)
    worker.owner = "worker-b"
    db = AsyncMock()
    tenant_id = uuid4()
    result = MagicMock()
    result.scalar_one_or_none.return_value = tenant_id
    db.execute.return_value = result

    selected = await worker._frontier_tenant_candidate(
        db,
        datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
    )

    assert selected == tenant_id
    statement = db.execute.await_args.args[0]
    sql = str(statement)
    assert "workflow_frontiers" in sql
    assert "workflow_executions" in sql
    assert "worker_owner" in sql
    assert "worker_lease_expires_at" in sql
    assert "pending" in sql
    assert "running" in sql


@pytest.mark.asyncio
async def test_frontier_tenant_candidate_returns_none_when_no_safe_frontier_exists() -> None:
    worker = object.__new__(DurableFrontierWorkflowWorker)
    worker.owner = "worker-b"
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    with pytest.raises(LookupError, match="no safely schedulable durable frontier"):
        await worker._frontier_tenant_candidate(
            db,
            datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
        )
