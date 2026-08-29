"""Execution terminalization boundary unit tests。"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.workflow.execution import WorkflowExecutionService


def _result(*, frontiers=None):
    """构造与 SQLAlchemy Result 终态查询契约一致的测试替身。"""
    return SimpleNamespace(
        scalar_one_or_none=lambda: None,
        scalars=lambda: SimpleNamespace(all=lambda: list(frontiers or [])),
    )


@pytest.mark.asyncio
async def test_terminal_transition_rejects_active_frontier() -> None:
    """Execution 仍有活动 Frontier 时必须拒绝 terminalization。"""
    execution = SimpleNamespace(tenant_id=uuid4(), id=uuid4(), worker_owner="worker:test", worker_attempt=3)
    frontier = SimpleNamespace(
        status="pending",
        worker_owner=None,
        attempt=0,
        worker_lease_expires_at=None,
    )
    db = SimpleNamespace(execute=AsyncMock(return_value=_result(frontiers=[frontier])))
    service = object.__new__(WorkflowExecutionService)
    service.db = db

    with pytest.raises(HTTPException, match="尚未执行的 Frontier"):
        await service._assert_no_active_frontiers_for_terminal_transition(
            execution,
            datetime.now(UTC).replace(tzinfo=None),
            "completed",
        )


@pytest.mark.asyncio
async def test_terminal_transition_allows_execution_without_active_frontier() -> None:
    """没有活动 Frontier 时允许继续进入 terminalization。"""
    db = SimpleNamespace(execute=AsyncMock(return_value=_result()))
    service = object.__new__(WorkflowExecutionService)
    service.db = db
    execution = SimpleNamespace(tenant_id=uuid4(), id=uuid4(), worker_owner=None, worker_attempt=0)

    await service._assert_no_active_frontiers_for_terminal_transition(
        execution,
        datetime.now(UTC).replace(tzinfo=None),
        "completed",
    )
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_terminal_transition_allows_owned_running_frontier() -> None:
    """当前 Worker 持有且租约有效的唯一 running Frontier 可以与 Execution 一起终态化。"""
    execution = SimpleNamespace(tenant_id=uuid4(), id=uuid4(), worker_owner="worker:test", worker_attempt=3)
    frontier = SimpleNamespace(
        status="running",
        worker_owner="worker:test",
        attempt=3,
        worker_lease_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=60),
        completed_at=None,
    )
    db = SimpleNamespace(execute=AsyncMock(return_value=_result(frontiers=[frontier])))
    service = object.__new__(WorkflowExecutionService)
    service.db = db
    now = datetime.now(UTC).replace(tzinfo=None)

    await service._assert_no_active_frontiers_for_terminal_transition(execution, now, "completed")

    assert frontier.status == "completed"
    assert frontier.completed_at == now
    assert frontier.worker_owner is None
    assert frontier.worker_lease_expires_at is None
