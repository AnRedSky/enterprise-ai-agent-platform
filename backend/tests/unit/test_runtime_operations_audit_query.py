"""II-07 Runtime 运维审计查询单元测试。

职责：验证审计查询的租户边界、分页约束、操作主体过滤和时间窗口校验。
边界：不启动服务、不访问真实数据库，不复制生产查询算法。
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.runtime_operations.service import RuntimeOperationsService


class _ScalarRows:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


@pytest.mark.asyncio
async def test_audit_query_is_tenant_scoped_and_paged():
    db = AsyncMock()
    db.scalar.return_value = 3
    db.execute.return_value = _ScalarRows(["audit-a", "audit-b"])
    tenant_id = uuid4()

    page, page_size, total, rows = await RuntimeOperationsService(db).audit_query(
        tenant_id,
        page=2,
        page_size=2,
        action="operator.workflow_execution.retry",
        resource_type="workflow_execution",
        outcome="success",
    )

    assert (page, page_size, total) == (2, 2, 3)
    assert rows == ["audit-a", "audit-b"]
    statement = db.execute.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "runtime_operation_audits.tenant_id" in compiled
    assert "operator.workflow_execution.retry" in compiled
    assert "workflow_execution" in compiled
    assert "success" in compiled


@pytest.mark.asyncio
async def test_audit_query_filters_by_actor_without_relaxing_tenant_scope():
    db = AsyncMock()
    db.scalar.return_value = 1
    db.execute.return_value = _ScalarRows(["audit-a"])
    tenant_id = uuid4()
    actor = str(uuid4())

    _, _, total, rows = await RuntimeOperationsService(db).audit_query(
        tenant_id,
        actor=actor,
    )

    assert total == 1
    assert rows == ["audit-a"]
    statement = db.execute.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "runtime_operation_audits.tenant_id" in compiled
    assert f"runtime_operation_audits.actor = '{actor}'" in compiled


@pytest.mark.asyncio
async def test_audit_query_rejects_reversed_time_window():
    db = AsyncMock()
    now = datetime.now(UTC).replace(tzinfo=None)

    with pytest.raises(ValueError, match="since must not be later than until"):
        await RuntimeOperationsService(db).audit_query(
            uuid4(),
            since=now,
            until=now - timedelta(seconds=1),
        )
    db.execute.assert_not_awaited()


def test_audit_query_page_size_is_bounded():
    assert RuntimeOperationsService._page(0, 1000) == (1, 100, 0)
    assert RuntimeOperationsService._page(3, 25) == (3, 25, 50)
