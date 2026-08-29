"""Durable Integration Event Persistence 单元测试。"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.integration.repository import IntegrationEventRepository
from app.services.integration.contract import IntegrationEvent


def make_event(**overrides: object) -> IntegrationEvent:
    values: dict[str, object] = {
        "tenant_id": uuid.uuid4(),
        "event_type": "workflow.execution.completed",
        "source": "workflow-runtime",
        "subject": "execution-001",
        "idempotency_key": "execution-001:completed:1",
        "payload": {"status": "completed"},
        "occurred_at": datetime.now(UTC),
    }
    values.update(overrides)
    return IntegrationEvent(**values)


@pytest.mark.asyncio
async def test_create_maps_contract_to_durable_record() -> None:
    db = MagicMock()
    db.flush = AsyncMock()
    event = make_event()
    record = await IntegrationEventRepository().create(db, event)
    assert record.id == event.event_id
    assert record.tenant_id == event.tenant_id
    assert record.status == "pending"
    assert record.attempt_count == 0
    assert record.payload == event.payload
    db.add.assert_called_once_with(record)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_scopes_lookup_by_tenant_and_event_id() -> None:
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = object()
    db.execute = AsyncMock(return_value=result)
    tenant_id = uuid.uuid4()
    event_id = uuid.uuid4()
    found = await IntegrationEventRepository().get(db, tenant_id, event_id)
    assert found is not None
    statement = db.execute.await_args.args[0]
    assert len(statement.whereclause.clauses) == 2


@pytest.mark.asyncio
async def test_list_pending_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        await IntegrationEventRepository().list_pending(MagicMock(), uuid.uuid4(), datetime.now(), 0)
