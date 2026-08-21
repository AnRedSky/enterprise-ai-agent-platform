from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.circuit_breaker import CircuitBreakerService, CircuitOpenError, _probe_context


def _service(state):
    db = MagicMock()
    db.execute = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: state)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return CircuitBreakerService(db)


def _state(*, success_count=2, half_open_max_calls=2, half_opened_at=None):
    return SimpleNamespace(
        state="half_open",
        failure_count=3,
        success_count=success_count,
        opened_at=datetime.now(UTC).replace(tzinfo=None),
        last_failure_at=None,
        half_opened_at=half_opened_at or datetime.now(UTC).replace(tzinfo=None),
        failure_threshold=3,
        recovery_timeout_ms=10_000,
        half_open_max_calls=half_open_max_calls,
    )


@pytest.mark.asyncio
async def test_half_open_probe_reservation_is_bounded_for_multiple_calls():
    tenant_id = uuid4()
    state = _state(success_count=1, half_open_max_calls=2)
    service = _service(state)
    config = {"circuit_breaker": {"enabled": True, "half_open_max_calls": 2}}

    result = await service.before_call(tenant_id, "agent:a:model:m", config)

    assert result == "half_open"
    assert state.state == "half_open"
    assert state.success_count == 2

    with pytest.raises(CircuitOpenError):
        await service.before_call(tenant_id, "agent:a:model:m", config)
    assert state.success_count == 2


@pytest.mark.asyncio
async def test_half_open_policy_mismatch_is_rejected_before_probe_reservation():
    tenant_id = uuid4()
    state = _state(success_count=1, half_open_max_calls=2)
    service = _service(state)

    with pytest.raises(HTTPException) as exc:
        await service.before_call(
            tenant_id,
            "agent:a:model:m",
            {"circuit_breaker": {"enabled": True, "half_open_max_calls": 3}},
        )

    assert exc.value.status_code == 409
    assert state.success_count == 1


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


@pytest.mark.asyncio
async def test_stale_half_open_success_does_not_close_new_recovery_window():
    tenant_id = uuid4()
    circuit_key = "agent:a:model:m"
    old_window = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=2)
    new_window = datetime.now(UTC).replace(tzinfo=None)
    state = _state(success_count=1, half_open_max_calls=1, half_opened_at=new_window)
    service = _service(state)
    token = _probe_context.set((tenant_id, circuit_key, old_window))
    try:
        await service.record_success(
            tenant_id,
            circuit_key,
            {"circuit_breaker": {"enabled": True, "half_open_max_calls": 1}},
        )
    finally:
        _probe_context.reset(token)

    assert state.state == "half_open"
    assert state.success_count == 1


@pytest.mark.asyncio
async def test_stale_half_open_failure_does_not_reopen_new_recovery_window():
    tenant_id = uuid4()
    circuit_key = "agent:a:model:m"
    old_window = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=2)
    new_window = datetime.now(UTC).replace(tzinfo=None)
    state = _state(success_count=1, half_open_max_calls=1, half_opened_at=new_window)
    service = _service(state)
    token = _probe_context.set((tenant_id, circuit_key, old_window))
    try:
        result = await service.record_failure(
            tenant_id,
            circuit_key,
            {"circuit_breaker": {"enabled": True, "half_open_max_calls": 1}},
        )
    finally:
        _probe_context.reset(token)

    assert result == "half_open"
    assert state.state == "half_open"
    assert state.success_count == 1
