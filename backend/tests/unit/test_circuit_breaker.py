from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.circuit_breaker import CircuitBreakerService, CircuitOpenError


def _service(state=None):
    db = MagicMock()
    db.execute = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: state)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return CircuitBreakerService(db), db


def _state(*, state="closed", failure_count=0, success_count=0, opened_at=None, half_opened_at=None,
           failure_threshold=3, recovery_timeout_ms=10_000, half_open_max_calls=1):
    return SimpleNamespace(
        state=state,
        failure_count=failure_count,
        success_count=success_count,
        opened_at=opened_at,
        last_failure_at=None,
        half_opened_at=half_opened_at,
        failure_threshold=failure_threshold,
        recovery_timeout_ms=recovery_timeout_ms,
        half_open_max_calls=half_open_max_calls,
    )


def test_validate_circuit_breaker_defaults_disabled():
    assert CircuitBreakerService.validate_config({}) == {
        "enabled": False,
        "key": None,
        "failure_threshold": 3,
        "recovery_timeout_ms": 10_000,
        "half_open_max_calls": 1,
    }


def test_validate_circuit_breaker_rejects_invalid_threshold():
    with pytest.raises(HTTPException) as exc:
        CircuitBreakerService.validate_config({"circuit_breaker": {"failure_threshold": 0}})
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_first_failure_persists_circuit_policy():
    tenant_id = uuid4()
    service, db = _service()
    result = await service.record_failure(
        tenant_id,
        "agent:a:model:m",
        {"circuit_breaker": {"enabled": True, "failure_threshold": 2, "recovery_timeout_ms": 5000, "half_open_max_calls": 2}},
    )
    state = db.add.call_args.args[0]
    assert result == "closed"
    assert state.state == "closed"
    assert state.failure_count == 1
    assert state.success_count == 0
    assert state.failure_threshold == 2
    assert state.recovery_timeout_ms == 5000
    assert state.half_open_max_calls == 2


@pytest.mark.asyncio
async def test_before_call_initializes_closed_state_counters():
    tenant_id = uuid4()
    service, db = _service()
    result = await service.before_call(
        tenant_id,
        "agent:a:model:m",
        {"circuit_breaker": {"enabled": True, "failure_threshold": 2}},
    )
    state = db.add.call_args.args[0]
    assert result == "closed"
    assert state.state == "closed"
    assert state.failure_count == 0
    assert state.success_count == 0
    assert state.failure_threshold == 2


@pytest.mark.asyncio
async def test_failure_threshold_opens_circuit():
    tenant_id = uuid4()
    state = _state(failure_count=2)
    service, _db = _service(state)
    result = await service.record_failure(
        tenant_id, "agent:a:model:m", {"circuit_breaker": {"enabled": True, "failure_threshold": 3}}
    )
    assert result == "open"
    assert state.state == "open"
    assert state.failure_count == 3
    assert state.opened_at is not None


@pytest.mark.asyncio
async def test_open_circuit_fast_fails_before_recovery():
    tenant_id = uuid4()
    state = _state(state="open", failure_count=3, opened_at=datetime.now(UTC).replace(tzinfo=None))
    service, _db = _service(state)
    with pytest.raises(CircuitOpenError) as exc:
        await service.before_call(
            tenant_id, "agent:a:model:m", {"circuit_breaker": {"enabled": True, "recovery_timeout_ms": 10_000}}
        )
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_existing_circuit_rejects_policy_drift():
    tenant_id = uuid4()
    state = _state(state="open", failure_count=3, opened_at=datetime.now(UTC).replace(tzinfo=None))
    service, _db = _service(state)
    with pytest.raises(HTTPException) as exc:
        await service.before_call(
            tenant_id,
            "agent:a:model:m",
            {"circuit_breaker": {"enabled": True, "recovery_timeout_ms": 200}},
        )
    assert exc.value.status_code == 409
    assert "policy mismatch" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_open_circuit_enters_half_open_after_persisted_recovery_timeout():
    tenant_id = uuid4()
    state = _state(
        state="open",
        failure_count=3,
        opened_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=2),
        recovery_timeout_ms=100,
    )
    service, _db = _service(state)
    result = await service.before_call(
        tenant_id, "agent:a:model:m", {"circuit_breaker": {"enabled": True, "recovery_timeout_ms": 100}}
    )
    assert result == "half_open"
    assert state.state == "half_open"
    assert state.success_count == 1


@pytest.mark.asyncio
async def test_half_open_success_closes_and_resets_circuit():
    tenant_id = uuid4()
    state = _state(
        state="half_open",
        failure_count=3,
        success_count=1,
        opened_at=datetime.now(UTC).replace(tzinfo=None),
        half_opened_at=datetime.now(UTC).replace(tzinfo=None),
    )
    service, _db = _service(state)
    await service.record_success(tenant_id, "agent:a:model:m", {"circuit_breaker": {"enabled": True}})
    assert state.state == "closed"
    assert state.failure_count == 0
    assert state.success_count == 0
    assert state.opened_at is None


@pytest.mark.asyncio
async def test_half_open_failure_reopens_and_resets_probe_count():
    tenant_id = uuid4()
    state = _state(
        state="half_open",
        failure_count=3,
        success_count=1,
        opened_at=None,
        half_opened_at=datetime.now(UTC).replace(tzinfo=None),
    )
    service, _db = _service(state)
    result = await service.record_failure(tenant_id, "agent:a:model:m", {"circuit_breaker": {"enabled": True}})
    assert result == "open"
    assert state.state == "open"
    assert state.success_count == 0
    assert state.opened_at is not None


@pytest.mark.asyncio
async def test_half_open_probe_slot_is_bounded():
    tenant_id = uuid4()
    state = _state(
        state="half_open",
        failure_count=3,
        success_count=1,
        opened_at=None,
        half_opened_at=datetime.now(UTC).replace(tzinfo=None),
    )
    service, _db = _service(state)
    with pytest.raises(CircuitOpenError):
        await service.before_call(
            tenant_id, "agent:a:model:m", {"circuit_breaker": {"enabled": True, "half_open_max_calls": 1}}
        )
