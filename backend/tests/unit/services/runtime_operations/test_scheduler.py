"""Runtime 告警周期调度单元测试。"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.runtime_operations.scheduler import RuntimeAlertScheduler


class _Result:
    def __init__(self, tenant_ids):
        self._tenant_ids = tenant_ids

    def scalars(self):
        return self

    def all(self):
        return self._tenant_ids


class _DiscoveryDB:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def execute(self, _statement):
        return _Result([TENANT_A, TENANT_B])


TENANT_A = uuid4()
TENANT_B = uuid4()


@pytest.mark.asyncio
async def test_runtime_alert_scheduler_processes_each_tenant_with_independent_session() -> None:
    service = AsyncMock()
    service.snapshot.side_effect = [4, 8]
    evaluator = AsyncMock()
    evaluator.evaluate.side_effect = [[{"transition": "firing"}], []]

    with (
        patch("app.services.runtime_operations.scheduler.SessionLocal", return_value=_DiscoveryDB()),
        patch("app.services.runtime_operations.scheduler.RuntimeOperationsEnterpriseService", return_value=service),
        patch("app.services.runtime_operations.scheduler.RuntimeAlertEvaluator", return_value=evaluator),
    ):
        # 为每个租户提供独立的异步 Session 上下文，避免跨租户事务复用。
        class _TenantDB:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def commit(self):
                return None

            async def rollback(self):
                return None

        with patch("app.services.runtime_operations.scheduler.SessionLocal", side_effect=[_DiscoveryDB(), _TenantDB(), _TenantDB()]):
            result = await RuntimeAlertScheduler(60).tick_once()

    assert result == {"discovered": 2, "sampled": 12, "transitions": 1}
    assert service.snapshot.await_count == 2
    assert evaluator.evaluate.await_count == 2


def test_runtime_alert_scheduler_rejects_non_positive_interval() -> None:
    with pytest.raises(ValueError):
        RuntimeAlertScheduler(0)
