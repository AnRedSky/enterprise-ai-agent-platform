"""验证 Runtime Notification Delivery 结果同步的 tenant 隔离边界。"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from app.services.integration.alert_lifecycle import AlertLifecycleService


@pytest.mark.asyncio
async def test_record_delivery_outcome_query_requires_tenant_scope() -> None:
    """验证 Notification outcome 查询必须同时约束 tenant 与 delivery ID。"""
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=None)
    tenant_id = uuid4()
    delivery_id = uuid4()

    result = await AlertLifecycleService(db).record_delivery_outcome(
        tenant_id,
        delivery_id,
        status="delivered",
    )

    assert result is None
    statement = db.scalar.await_args.args[0]
    predicates = list(statement.whereclause.get_children())
    compiled = statement.compile()
    assert tenant_id in compiled.params.values()
    assert delivery_id in compiled.params.values()
    assert any(getattr(predicate, "left", None).name == "tenant_id" for predicate in predicates)
    assert any(getattr(predicate, "left", None).name == "webhook_delivery_id" for predicate in predicates)
