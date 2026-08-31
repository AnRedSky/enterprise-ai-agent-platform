from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.runtime_operations.diagnostics import RuntimeDiagnosticsService


def test_diagnostics_window_is_bounded() -> None:
    hours, since = RuntimeDiagnosticsService._since(999)

    assert hours == 168
    assert since.tzinfo is None


@pytest.mark.parametrize("window_hours", [0, -1])
def test_diagnostics_window_never_returns_non_positive(window_hours: int) -> None:
    hours, _ = RuntimeDiagnosticsService._since(window_hours)

    assert hours == 1


@pytest.mark.asyncio
async def test_worker_diagnostics_keeps_liveness_unknown_without_heartbeat() -> None:
    db = MagicMock()
    status_result = MagicMock()
    status_result.all.return_value = [("running", 2), ("pending", 1)]
    lease_result = MagicMock()
    lease_result.one.return_value = (0, 2, 1)
    owner_result = MagicMock()
    owner_result.all.return_value = [("worker-a", 2)]
    error_result = MagicMock()
    error_result.all.return_value = []
    db.execute = AsyncMock(side_effect=[status_result, lease_result, owner_result, error_result])

    result = await RuntimeDiagnosticsService(db).worker(uuid4())

    assert result["liveness"] == "unknown"
    assert result["liveness_reason_code"] == "NO_DURABLE_HEARTBEAT_FACT"
    assert result["frontier"]["running"] == 2
    assert result["leases"]["expired"] == 1
    assert result["owners"] == [{"worker_owner": "worker-a", "claim_count": 2}]


@pytest.mark.asyncio
async def test_scheduler_diagnostics_is_tenant_scoped_and_does_not_infer_liveness() -> None:
    db = MagicMock()
    db.scalar = AsyncMock(side_effect=[3, 1, 5])
    trigger_result = MagicMock()
    trigger_result.all.return_value = []
    db.execute = AsyncMock(return_value=trigger_result)

    result = await RuntimeDiagnosticsService(db).scheduler(uuid4())

    assert result["liveness"] == "unknown"
    assert result["liveness_reason_code"] == "NO_DURABLE_HEARTBEAT_FACT"
    assert result["durable"] == {
        "enabled_scheduled_triggers": 3,
        "disabled_scheduled_triggers": 1,
        "pending_frontier_items": 5,
    }
