"""Durable Frontier / Execution 原子租约心跳单元测试。"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.frontier_lease_repository import renew_owned_frontier_lease


class _Result:
    """最小化模拟 SQLAlchemy execute 返回结果。"""

    def __init__(self, rowcount: int = 1, execution_id=None, scalar_value=None):
        self.rowcount = rowcount
        self._execution_id = execution_id
        self._scalar_value = scalar_value

    def scalar_one_or_none(self):
        """返回查询得到的标量值。"""
        if self._execution_id is not None:
            return self._execution_id
        return self._scalar_value


@pytest.mark.asyncio
async def test_heartbeat_renews_frontier_and_execution_in_same_transaction():
    """验证心跳先解析 Execution，再原子刷新 Execution 与 Frontier。"""
    frontier_id = uuid4()
    execution_id = uuid4()
    db = SimpleNamespace()
    db.execute = AsyncMock(side_effect=[_Result(execution_id=execution_id), _Result(1), _Result(1)])
    db.flush = AsyncMock()
    db.rollback = AsyncMock()

    result = await renew_owned_frontier_lease(
        db,
        frontier_id=frontier_id,
        worker_owner="worker:test",
        attempt=3,
        lease_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=60),
        now=datetime.now(UTC).replace(tzinfo=None),
    )

    assert result is True
    assert db.execute.await_count == 3
    db.flush.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_heartbeat_rolls_back_when_execution_lease_cannot_be_renewed():
    """验证 Execution 租约无法续期且仍非终态时，不会继续刷新 Frontier。"""
    frontier_id = uuid4()
    execution_id = uuid4()
    db = SimpleNamespace()
    db.execute = AsyncMock(
        side_effect=[_Result(execution_id=execution_id), _Result(0), _Result(scalar_value="running")]
    )
    db.flush = AsyncMock()
    db.rollback = AsyncMock()

    result = await renew_owned_frontier_lease(
        db,
        frontier_id=frontier_id,
        worker_owner="worker:test",
        attempt=3,
        lease_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=60),
        now=datetime.now(UTC).replace(tzinfo=None),
    )

    assert result is False
    assert db.execute.await_count == 3
    db.rollback.assert_awaited_once()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_heartbeat_accepts_execution_terminalization_without_frontier_refresh():
    """验证 Execution 已进入终态时，心跳停止续租但不发出租约丢失信号。"""
    frontier_id = uuid4()
    execution_id = uuid4()
    db = SimpleNamespace()
    db.execute = AsyncMock(
        side_effect=[_Result(execution_id=execution_id), _Result(0), _Result(scalar_value="completed")]
    )
    db.flush = AsyncMock()
    db.rollback = AsyncMock()

    result = await renew_owned_frontier_lease(
        db,
        frontier_id=frontier_id,
        worker_owner="worker:test",
        attempt=3,
        lease_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=60),
        now=datetime.now(UTC).replace(tzinfo=None),
    )

    assert result is True
    assert db.execute.await_count == 3
    db.rollback.assert_awaited_once()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_heartbeat_rolls_back_when_frontier_lease_cannot_be_renewed():
    """验证 Frontier 租约无法续期时，Execution 续租也不会被提交。"""
    frontier_id = uuid4()
    execution_id = uuid4()
    db = SimpleNamespace()
    db.execute = AsyncMock(side_effect=[_Result(execution_id=execution_id), _Result(1), _Result(0)])
    db.flush = AsyncMock()
    db.rollback = AsyncMock()

    result = await renew_owned_frontier_lease(
        db,
        frontier_id=frontier_id,
        worker_owner="worker:test",
        attempt=3,
        lease_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=60),
        now=datetime.now(UTC).replace(tzinfo=None),
    )

    assert result is False
    assert db.execute.await_count == 3
    db.rollback.assert_awaited_once()
    db.flush.assert_not_awaited()
