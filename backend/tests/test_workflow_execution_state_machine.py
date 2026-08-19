from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.workflow_execution import WorkflowExecutionService


@pytest.mark.asyncio
async def test_pending_execution_can_start_and_complete():
    db = AsyncMock()
    db.refresh = AsyncMock()
    service = WorkflowExecutionService(db)
    execution = SimpleNamespace(
        id=uuid4(), status="pending", current_node_id=None, started_at=None,
        ended_at=None, output_data=None, error_code=None, error_message=None,
    )

    await service.transition(execution, "running", node_id="start")
    assert execution.status == "running"
    assert execution.current_node_id == "start"
    assert execution.started_at is not None

    await service.transition(execution, "completed", output_data={"ok": True})
    assert execution.status == "completed"
    assert execution.output_data == {"ok": True}
    assert execution.ended_at is not None
    assert execution.current_node_id is None


@pytest.mark.asyncio
async def test_terminal_execution_cannot_transition_again():
    db = AsyncMock()
    service = WorkflowExecutionService(db)
    execution = SimpleNamespace(
        id=uuid4(), status="completed", current_node_id=None, started_at=None,
        ended_at=None, output_data=None, error_code=None, error_message=None,
    )

    with pytest.raises(HTTPException) as exc:
        await service.transition(execution, "running")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_pending_execution_can_be_cancelled_but_running_cannot_complete_twice():
    db = AsyncMock()
    db.refresh = AsyncMock()
    service = WorkflowExecutionService(db)
    execution = SimpleNamespace(
        id=uuid4(), status="pending", current_node_id=None, started_at=None,
        ended_at=None, output_data=None, error_code=None, error_message=None,
    )

    await service.transition(execution, "cancelled")
    assert execution.status == "cancelled"
    assert execution.ended_at is not None

    with pytest.raises(HTTPException) as exc:
        await service.transition(execution, "failed")
    assert exc.value.status_code == 409
