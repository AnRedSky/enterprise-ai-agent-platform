from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.workflow import WorkflowExecutionService


def _execution(*, status: str) -> SimpleNamespace:
    """构造满足 Workflow Execution 状态机契约的测试对象。"""
    return SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), created_by=uuid4(),
        status=status, current_node_id=None, started_at=None, ended_at=None, output_data=None,
        error_code=None, error_message=None, input_data={}, worker_owner=None, worker_attempt=0,
    )


def _db() -> AsyncMock:
    """构造异步 Session 测试替身，并为同步 SQLAlchemy Result 方法提供确定返回值。"""
    db = AsyncMock()
    db.add = Mock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))
    return db


@pytest.mark.asyncio
async def test_pending_execution_can_start_and_complete():
    db = _db()
    service = WorkflowExecutionService(db)
    execution = _execution(status="pending")

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
    db = _db()
    service = WorkflowExecutionService(db)
    execution = _execution(status="completed")

    with pytest.raises(HTTPException) as exc:
        await service.transition(execution, "running")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_pending_execution_can_be_cancelled_but_running_cannot_complete_twice():
    db = _db()
    service = WorkflowExecutionService(db)
    execution = _execution(status="pending")

    await service.transition(execution, "cancelled")
    assert execution.status == "cancelled"
    assert execution.ended_at is not None

    with pytest.raises(HTTPException) as exc:
        await service.transition(execution, "failed")
    assert exc.value.status_code == 409
