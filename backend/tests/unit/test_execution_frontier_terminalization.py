"""Workflow Execution 与 Durable Frontier 原子终态单元测试。

职责：验证 Runtime 完成或失败时，当前 Worker 的唯一 running Frontier 与 Execution 在同一事务内一致终止。
边界：不连接 PostgreSQL；只验证 Execution Service 的状态机与 Frontier fencing Contract。
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.workflow.execution import WorkflowExecutionService


def _future_lease() -> datetime:
    """生成相对当前时间仍有效的测试租约，避免固定历史时间使单元测试失效。"""
    return datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)


def _execution() -> MagicMock:
    execution = MagicMock()
    execution.id = uuid4()
    execution.tenant_id = uuid4()
    execution.status = "running"
    execution.worker_owner = "worker:b6"
    execution.worker_attempt = 3
    execution.worker_lease_expires_at = _future_lease()
    execution.created_by = uuid4()
    execution.current_node_id = "node-a"
    return execution


def _frontier(execution: MagicMock, status: str = "running") -> MagicMock:
    frontier = MagicMock()
    frontier.id = uuid4()
    frontier.tenant_id = execution.tenant_id
    frontier.execution_id = execution.id
    frontier.status = status
    frontier.worker_owner = execution.worker_owner
    frontier.attempt = execution.worker_attempt
    frontier.worker_lease_expires_at = _future_lease()
    frontier.completed_at = None
    return frontier


def _service(db: AsyncMock) -> WorkflowExecutionService:
    service = WorkflowExecutionService(db)
    service.governance.trace = AsyncMock()
    service.governance.audit = AsyncMock()
    service._lock_execution = AsyncMock(side_effect=lambda execution: execution)
    return service


@pytest.mark.asyncio
@pytest.mark.parametrize("target_status", ["completed", "failed"])
async def test_terminal_execution_closes_owned_running_frontier_atomically(target_status: str) -> None:
    """验证 Execution terminalization 会在同一事务内关闭当前 Worker 的 running Frontier。"""
    db = AsyncMock()
    execution = _execution()
    frontier = _frontier(execution)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [frontier]
    db.execute.return_value = result

    service = _service(db)
    await service.transition(execution, target_status, actor_id=execution.created_by)

    assert execution.status == target_status
    assert frontier.status == target_status
    assert frontier.worker_owner is None
    assert frontier.worker_lease_expires_at is None
    assert frontier.completed_at is not None
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(execution)


@pytest.mark.asyncio
async def test_terminal_execution_rejects_pending_sibling_frontier() -> None:
    """验证存在尚未执行 sibling Frontier 时不能伪造 Execution terminalization。"""
    db = AsyncMock()
    execution = _execution()
    frontier = _frontier(execution, status="pending")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [frontier]
    db.execute.return_value = result

    service = _service(db)
    with pytest.raises(HTTPException, match="尚未执行的 Frontier"):
        await service.transition(execution, "completed", actor_id=execution.created_by)

    assert execution.status == "running"
    assert frontier.status == "pending"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_terminal_execution_rejects_expired_owned_running_frontier() -> None:
    """验证当前 Worker 的 running Frontier 租约过期时禁止伪造终态收敛。"""
    db = AsyncMock()
    execution = _execution()
    frontier = _frontier(execution)
    frontier.worker_lease_expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [frontier]
    db.execute.return_value = result

    service = _service(db)
    with pytest.raises(HTTPException, match="lease 已失效"):
        await service.transition(execution, "completed", actor_id=execution.created_by)

    assert execution.status == "running"
    assert frontier.status == "running"
    db.commit.assert_not_awaited()
