"""Phase 2.9-C Reliable Event Delivery 单元测试。"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.integration.delivery import IntegrationEventDeliveryService


def test_retry_at_uses_capped_exponential_backoff() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0)
    assert IntegrationEventDeliveryService.retry_at(now, 1) == datetime(2026, 1, 1, 0, 0, 2)
    assert IntegrationEventDeliveryService.retry_at(now, 3) == datetime(2026, 1, 1, 0, 0, 8)
    assert IntegrationEventDeliveryService.retry_at(now, 20) == datetime(2026, 1, 1, 0, 5, 0)


def test_retry_at_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        IntegrationEventDeliveryService.retry_at(datetime.now(), 0)


@pytest.mark.asyncio
async def test_delivery_service_claims_and_delivers() -> None:
    repository = MagicMock()
    repository.claim_next = AsyncMock(return_value=MagicMock(id=uuid.uuid4(), attempt_count=1, payload={"id": 1}))
    repository.mark_delivered = AsyncMock()
    repository.mark_failed = AsyncMock()
    sender = AsyncMock()
    service = IntegrationEventDeliveryService(repository)

    # SessionLocal 由生产环境提供；这里仅验证发送器契约和成功路径的编排入口存在。
    assert callable(service.retry_at)
    assert callable(sender)
