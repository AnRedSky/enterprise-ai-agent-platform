"""Runtime Notification Routing scheduler 单元测试。"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.runtime_operations.notification_scheduler import RuntimeNotificationScheduler

TENANT_A = uuid4()
TENANT_B = uuid4()


class _Result:
    def scalars(self):
        return self

    def all(self):
        return [TENANT_A, TENANT_B]


class _DiscoveryDB:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def execute(self, _statement):
        return _Result()


class _TenantDB:
    def __init__(self):
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


@pytest.mark.asyncio
async def test_notification_scheduler_routes_each_tenant_in_independent_session():
    first = _TenantDB()
    second = _TenantDB()
    dispatcher = AsyncMock()
    dispatcher.dispatch_tenant.side_effect = [3, 2]

    with (
        patch(
            "app.services.runtime_operations.notification_scheduler.SessionLocal",
            side_effect=[_DiscoveryDB(), first, second],
        ),
        patch(
            "app.services.runtime_operations.notification_scheduler.NotificationDispatcher",
            return_value=dispatcher,
        ),
    ):
        result = await RuntimeNotificationScheduler(30, batch_size=50).tick_once()

    assert result == {"discovered": 2, "created": 5}
    assert dispatcher.dispatch_tenant.await_count == 2
    assert first.commit.await_count == 1
    assert second.commit.await_count == 1
    assert first.rollback.await_count == 0
    assert second.rollback.await_count == 0


def test_notification_scheduler_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        RuntimeNotificationScheduler(0)
    with pytest.raises(ValueError):
        RuntimeNotificationScheduler(30, batch_size=0)
    with pytest.raises(ValueError):
        RuntimeNotificationScheduler(30, batch_size=1001)
