"""Durable Frontier 租约恢复边界的单元测试。

验证 Frontier 过期不能单独触发 Recovery；关联 Execution 仍持有有效 lease 时必须继续阻止回收。
"""

from datetime import datetime

from sqlalchemy.dialects import postgresql

from app.services.workflow.frontier_repository import _execution_recoverable_filter


def test_execution_recoverable_filter_requires_unowned_or_expired_lease() -> None:
    now = datetime(2026, 8, 27, 12, 0, 0)
    expression = _execution_recoverable_filter(now)
    compiled = str(expression.compile(dialect=postgresql.dialect()))

    assert "worker_owner IS NULL" in compiled
    assert "worker_lease_expires_at IS NULL" in compiled
    assert "worker_lease_expires_at <=" in compiled


def test_execution_recoverable_filter_does_not_allow_active_owner_as_standalone_condition() -> None:
    now = datetime(2026, 8, 27, 12, 0, 0)
    expression = _execution_recoverable_filter(now)
    compiled = str(expression.compile(dialect=postgresql.dialect()))

    # 恢复条件必须是 OR 组合；只有 owner 存在且 lease 未过期时，表达式整体才应为 false。
    assert compiled.count(" OR ") == 2
