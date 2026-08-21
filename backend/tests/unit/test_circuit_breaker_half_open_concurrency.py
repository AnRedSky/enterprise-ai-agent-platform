from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.circuit_breaker import CircuitBreakerService


def _service(state):
    db = MagicMock()
    db.execute = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: state)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return CircuitBreakerService(db)


def _state(*, success_count=2, half_open_max_calls=2):
    return SimpleNamespace(
        state="half_open",
        failure_count=3,
        success_count=success_count,
        opened_at=datetime.now(UTC).replace(tzinfo=None),
        last_failure_at=None,
        half_opened_at=datetime.now(UTC).replace(tzinfo=None),
        failure_threshold=3,
        recovery_timeout_ms=10_000,
        half_open_max_calls=half_open_max_calls,
    )


@pytest.mark.asyncio
async def test_half_open_success_releases_only_one_probe_slot():
    tenant_id = uuid4()
    state = _state(success_count=2, half_open_max_calls=2)
    service = _service(state)

    await service.record_success(
        tenant_id,
        "agent:a:model:m",
        {"circuit_breaker": {"enabled": True, "half_open_max_calls": 2}},
    )

    assert state.state == "half_open"
    assert state.success_count == 1


@pytest.mark.asyncio
async def test_half_open_closes_only_after_all_reserved_probes_succeed():
    tenant_id = uuid4()
    state = _state(success_count=2, half_open_max_calls=2)
    service = _service(state)
    config = {"circuit_breaker": {"enabled": True, "half_open_max_calls": 2}}

    await service.record_success(tenant_id, "agent:a:model:m", config)
    assert state.state == "half_open"
    assert state.success_count == 1

    await service.record_success(tenant_id, "agent:a:model:m", config)
    assert state.state == "closed"
    assert state.success_count == 0
    assert state.failure_count == 0


@pytest.mark.asyncio
async def test_half_open_failure_after_other_probe_success_reopens_circuit():
    tenant_id = uuid4()
    state = _state(success_count=2, half_open_max_calls=2)
    service = _service(state)
    config = {"circuit_breaker": {"enabled": True, "half_open_max_calls": 2}}

    await service.record_success(tenant_id, "agent:a:model:m", config)
    assert state.success_count == 1

    result = await service.record_failure(tenant_id, "agent:a:model:m", config)

    assert result == "open"
    assert state.state == "open"
    assert state.success_count == 0
