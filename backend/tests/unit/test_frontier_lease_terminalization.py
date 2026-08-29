"""Durable Frontier lease terminalization 回归测试。

职责：验证 Runtime 已经把 WorkflowExecution 推进终态后，Frontier heartbeat 不会把正常 terminalization
误判为失效 Worker 并取消外层 Runtime。
边界：只覆盖 lease repository 的终态 fencing 语义，不替代 PostgreSQL Real API Runtime 验收。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.services.workflow.frontier_lease_repository import renew_owned_frontier_lease


class _FakeResult:
    """为 lease repository 提供最小异步查询结果。"""

    def __init__(self, *, scalar=None, rowcount: int | None = None) -> None:
        self._scalar = scalar
        self.rowcount = rowcount

    def scalar_one_or_none(self):
        """返回预设标量结果。"""
        return self._scalar


class _FakeSession:
    """按固定 SQL 操作顺序模拟 lease heartbeat 的短事务。"""

    def __init__(self, results: list[_FakeResult]) -> None:
        self._results = iter(results)
        self.rollback_count = 0

    async def execute(self, _statement):
        """返回下一项预设数据库结果。"""
        return next(self._results)

    async def rollback(self) -> None:
        """记录 rollback 调用。"""
        self.rollback_count += 1

    async def flush(self) -> None:
        """提供成功路径所需的最小 Session 接口。"""


@pytest.mark.asyncio
async def test_terminal_execution_is_not_reported_as_lease_loss() -> None:
    """Execution 已终态时 heartbeat 必须保持 True，避免取消正常完成的 Runtime。"""
    execution_id = uuid4()
    db = _FakeSession(
        [
            _FakeResult(scalar=execution_id),
            _FakeResult(rowcount=0),
            _FakeResult(scalar="completed"),
        ]
    )

    owned = await renew_owned_frontier_lease(
        db,
        frontier_id=uuid4(),
        worker_owner="worker:test",
        attempt=1,
        lease_expires_at=datetime(2026, 8, 29, 12, 0, 1),
        now=datetime(2026, 8, 29, 12, 0, 0),
    )

    assert owned is True
    assert db.rollback_count == 1


@pytest.mark.asyncio
async def test_non_terminal_ownership_loss_still_reports_false() -> None:
    """Execution 仍可运行但 ownership 已失效时 heartbeat 必须继续报告 lease loss。"""
    execution_id = uuid4()
    db = _FakeSession(
        [
            _FakeResult(scalar=execution_id),
            _FakeResult(rowcount=0),
            _FakeResult(scalar="running"),
        ]
    )

    owned = await renew_owned_frontier_lease(
        db,
        frontier_id=uuid4(),
        worker_owner="worker:test",
        attempt=1,
        lease_expires_at=datetime(2026, 8, 29, 12, 0, 1),
        now=datetime(2026, 8, 29, 12, 0, 0),
    )

    assert owned is False
    assert db.rollback_count == 1
