from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.services.runtime_operations.audit_trace_correlation import RuntimeAuditTraceCorrelationService


TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000002")
AUDIT_ID = UUID("00000000-0000-0000-0000-000000000003")


def _execution():
    return SimpleNamespace(id=EXECUTION_ID)


def _trace(trace_id="trace-1"):
    return SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000004"),
        tenant_id=TENANT_ID,
        execution_id=EXECUTION_ID,
        trace_id=trace_id,
    )


def _audit():
    return SimpleNamespace(
        id=AUDIT_ID,
        tenant_id=TENANT_ID,
        workflow_execution_id=EXECUTION_ID,
        operator_action_id=None,
        trace_id="trace-1",
    )


@pytest.mark.asyncio
async def test_trace_focus_is_returned_outside_the_paginated_page():
    # This test replaces all DB-facing collaborators, so the DB object itself must
    # remain synchronous to avoid creating un-awaited AsyncMock.execute coroutines
    # during pytest teardown.
    service = RuntimeAuditTraceCorrelationService(MagicMock())
    focused = [_trace()]
    service._execution_ids_from_trace = AsyncMock(return_value=[EXECUTION_ID])
    service._focused_traces = AsyncMock(return_value=focused)
    service.by_execution = AsyncMock(
        return_value={
            "execution": _execution(),
            "traces": {"items": [], "page": 9, "page_size": 1, "total": 100},
            "audits": {"items": [], "page": 1, "page_size": 50, "total": 0},
            "operator_actions": [],
        }
    )

    result = await service.by_trace(TENANT_ID, "trace-1", trace_page=9, trace_page_size=1)

    assert result["traces"]["items"] == []
    assert result["focused_traces"] == focused
    service._focused_traces.assert_awaited_once_with(TENANT_ID, "trace-1")


@pytest.mark.asyncio
async def test_audit_focus_is_returned_outside_the_paginated_page():
    service = RuntimeAuditTraceCorrelationService(MagicMock())
    audit = _audit()
    service._audit = AsyncMock(return_value=audit)
    service.by_execution = AsyncMock(
        return_value={
            "execution": _execution(),
            "traces": {"items": [], "page": 1, "page_size": 50, "total": 0},
            "audits": {"items": [], "page": 7, "page_size": 1, "total": 100},
            "operator_actions": [],
        }
    )
    service._focused_traces = AsyncMock(return_value=[])
    service._execution_id_from_audit = AsyncMock(return_value=EXECUTION_ID)

    result = await service.by_audit(TENANT_ID, AUDIT_ID, audit_page=7, audit_page_size=1)

    assert result["audits"]["items"] == []
    assert result["focused_audit"] is audit
    assert result["focus_audit_id"] == AUDIT_ID
