"""Phase 2.9 Enterprise Integration 事件契约单元测试。

职责：验证事件身份、租户隔离、幂等作用域、版本和序列化边界。
边界：只测试领域契约，不依赖 PostgreSQL、HTTP 或消息中间件。
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.services.integration import IntegrationEvent


def _event(**overrides: object) -> IntegrationEvent:
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


def test_event_contract_generates_identity_and_serializes_stable_fields() -> None:
    event = _event()

    assert event.event_id
    assert event.schema_version == 1
    serialized = event.as_dict()
    assert serialized["event_id"] == str(event.event_id)
    assert serialized["tenant_id"] == str(event.tenant_id)
    assert serialized["occurred_at"] == event.occurred_at.isoformat()


def test_idempotency_scope_contains_tenant_source_and_event_type() -> None:
    tenant_id = uuid.uuid4()
    event = _event(tenant_id=tenant_id, source="webhook", idempotency_key="abc")

    assert event.deduplication_scope == (tenant_id, "webhook", "workflow.execution.completed", "abc")


def test_invalid_event_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="event_type"):
        _event(event_type="Workflow Execution Completed")


def test_naive_occurred_at_is_rejected() -> None:
    with pytest.raises(ValueError, match="时区"):
        _event(occurred_at=datetime.now())


def test_schema_version_must_start_at_one() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        _event(schema_version=0)
