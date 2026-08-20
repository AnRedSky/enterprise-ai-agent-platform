from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.circuit_breaker import CircuitBreakerService, CircuitOpenError


def _service(state=None):
    db = AsyncMock()
    result = SimpleNamespace(scalar_one_or_none=lambda: state)
    db.execute.return_value = result
    return CircuitBreakerService(db), db


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
async def test_failure_threshold_opens_circuit():
    tenant_id = uuid4()
    state = SimpleNamespace(
        state="closed", failure_count=2, success_count=0,
        opened_at=None, last_failure_at=None, half_opened_at=None,
    )
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
    state = SimpleNamespace(
        state="open", failure_count=3, success_count=0,
        opened_at=datetime.now(UTC).replace(tzinfo=None), last_failure_at=None, half_opened_at=None,
    )
    service, _db = _service(state)
    with pytest.raises(CircuitOpenError) as exc:
        await service.before_call(
            tenant_id, "agent:a:model:m", {"circuit_breaker": {"enabled": True, "recovery_timeout_ms": 10_000}}
        )
    assert exc.value.status_code == 503

@pytest.mark.asyncio
async def test_open_circuit_enters_half_open_after_recovery():
    tenant_id = uuid4()
    state = SimpleNamespace(
        state="open", failure_count=3, success_count=0,
        opened_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=2),
        last_failure_at=None, half_opened_at=None,
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
    state = SimpleNamespace(
        state="half_open", failure_count=3, success_count=1,
        opened_at=datetime.now(UTC).replace(tzinfo=None), last_failure_at=None,
        half_opened_at=datetime.now(UTC).replace(tzinfo=None),
    )
    service, _db = _service(state)
    await service.record_success(tenant_id, "agent:a:model:m", {"circuit_breaker": {"enabled": True}})
    assert state.state == "closed"
    assert state.failure_count == 0
    assert state.success_count == 0
    assert state.opened_at is None

@pytest.mark.asyncio
async def test_half_open_probe_slot_is_bounded():
    tenant_id = uuid4()
    state = SimpleNamespace(
        state="half_open", failure_count=3, success_count=1,
        opened_at=None, last_failure_at=None, half_opened_at=datetime.now(UTC).replace(tzinfo=None),
    )
    service, _db = _service(state)
    with pytest.raises(CircuitOpenError):
        await service.before_call(
            tenant_id, "agent:a:model:m", {"circuit_breaker": {"enabled": True, "half_open_max_calls": 1}}
        )
