"""Execution terminalization boundary unit tests。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.workflow.execution import WorkflowExecutionService


@pytest.mark.asyncio
async def test_terminal_transition_rejects_active_frontier() -> None:
    """Execution 仍有活动 Frontier 时必须拒绝 completed/failed terminalization。"""
    db = SimpleNamespace(execute=AsyncMock())
    result = SimpleNamespace(scalar_one_or_none=lambda: uuid4())
    db.execute.return_value = result
    service = object.__new__(WorkflowExecutionService)
    service.db = db
    execution = SimpleNamespace(tenant_id=uuid4(), id=uuid4())

    with pytest.raises(HTTPException, match="仍存在活动 Frontier"):
        await service._assert_no_active_frontiers_for_terminal_transition(execution)


@pytest.mark.asyncio
async def test_terminal_transition_allows_execution_without_active_frontier() -> None:
    """没有活动 Frontier 时允许继续进入 terminalization。"""
    db = SimpleNamespace(execute=AsyncMock())
    result = SimpleNamespace(scalar_one_or_none=lambda: None)
    db.execute.return_value = result
    service = object.__new__(WorkflowExecutionService)
    service.db = db
    execution = SimpleNamespace(tenant_id=uuid4(), id=uuid4())

    await service._assert_no_active_frontiers_for_terminal_transition(execution)
    db.execute.assert_awaited_once()
