"""Durable Frontier Recovery Contract 单元测试。

职责：验证过期 Frontier 回收不会重新激活已经 terminalize 的 Execution。
边界：只检查 Recovery 查询契约与状态收敛，不复制生产数据库更新算法。
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.services.workflow.frontier_repository import recover_expired_frontiers


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class _FakeSession:
    def __init__(self, values):
        self.values = values
        self.statement = None
        self.flush_count = 0

    async def execute(self, statement):
        self.statement = statement
        return _ScalarResult(self.values)

    async def flush(self):
        self.flush_count += 1


@pytest.mark.asyncio
async def test_recovery_query_excludes_terminal_execution_frontiers():
    frontier = SimpleNamespace(
        status="running",
        worker_owner="worker-a",
        worker_lease_expires_at=datetime(2026, 8, 27, 10, 0),
        available_at=None,
        error_code=None,
        error_message=None,
    )
    db = _FakeSession([frontier])

    recovered = await recover_expired_frontiers(
        db,
        now=datetime(2026, 8, 27, 11, 0),
        limit=10,
    )

    sql = str(db.statement.compile(dialect=postgresql.dialect()))
    assert "workflow_executions.status IN" in sql
    assert recovered == [frontier]
    assert frontier.status == "retry_wait"
    assert frontier.worker_owner is None
    assert frontier.worker_lease_expires_at is None
    assert frontier.error_code == "FRONTIER_LEASE_EXPIRED"
    assert db.flush_count == 1


def test_recovery_limit_must_be_positive():
    with pytest.raises(ValueError, match="limit must be positive"):
        import asyncio

        asyncio.run(
            recover_expired_frontiers(
                _FakeSession([]),
                now=datetime(2026, 8, 27, 11, 0),
                limit=0,
            )
        )
