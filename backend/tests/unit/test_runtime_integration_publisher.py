from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.integration_event import IntegrationEventRecord
from app.services.integration.publisher import RuntimeIntegrationEventPublisher


@pytest.mark.asyncio
async def test_publish_uses_current_transaction_and_unified_event_contract() -> None:
    db = MagicMock()

    @asynccontextmanager
    async def savepoint():
        yield

    db.begin_nested = savepoint
    repository = MagicMock()
    repository.create = AsyncMock()
    publisher = RuntimeIntegrationEventPublisher(db)
    publisher.repository = repository
    expected = IntegrationEventRecord(
        id=uuid4(),
        tenant_id=uuid4(),
        event_type="workflow.execution.completed",
        schema_version=1,
        source="workflow-runtime",
        subject=str(uuid4()),
        idempotency_key="workflow-execution:test:completed",
        occurred_at=None,
        request_id="request-test",
        trace_id="trace-test",
        payload={"execution_id": "test"},
        metadata_json={},
        status="pending",
        attempt_count=0,
    )
    repository.create.return_value = expected

    record = await publisher.publish(
        tenant_id=expected.tenant_id,
        event_type=expected.event_type,
        source=expected.source,
        subject=expected.subject,
        idempotency_key=expected.idempotency_key,
        payload=expected.payload,
        request_id=expected.request_id,
        trace_id=expected.trace_id,
    )

    assert record is expected
    event = repository.create.await_args.args[1]
    assert event.tenant_id == expected.tenant_id
    assert event.event_type == expected.event_type
    assert event.source == expected.source
    assert event.subject == expected.subject
    assert event.idempotency_key == expected.idempotency_key
    assert event.request_id == expected.request_id
    assert event.trace_id == expected.trace_id
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
