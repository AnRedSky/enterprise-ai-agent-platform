"""验证 Runtime 运维基础服务的 Audit tenant boundary 查询入口。"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.runtime_operations.service import RuntimeOperationsService


@pytest.mark.asyncio
async def test_audit_list_is_tenant_scoped_and_bounded() -> None:
    """Audit 查询必须只按目标租户读取，并将 limit 限制在 1 到 1000。"""
    tenant_id = uuid4()
    expected = [MagicMock(), MagicMock()]
    result = MagicMock()
    result.scalars.return_value.all.return_value = expected
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    audits = await RuntimeOperationsService(db).audit_list(tenant_id, limit=5000)

    assert audits == expected
    statement = db.execute.await_args.args[0]
    compiled = str(statement)
    assert "runtime_operation_audits.tenant_id" in compiled
    assert statement._limit_clause.value == 1000
