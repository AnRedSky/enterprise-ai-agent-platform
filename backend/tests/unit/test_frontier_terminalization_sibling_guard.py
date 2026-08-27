from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.frontier_progression import (
    FrontierProgressionContractError,
    _assert_no_active_sibling_frontiers_for_terminal_execution,
)


@pytest.mark.asyncio
async def test_terminal_execution_rejects_active_sibling_frontier() -> None:
    db = AsyncMock()
    result = SimpleNamespace(scalar_one_or_none=lambda: uuid4())
    db.execute.return_value = result
    frontier = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), execution_id=uuid4())

    with pytest.raises(FrontierProgressionContractError, match="活动 sibling Frontier"):
        await _assert_no_active_sibling_frontiers_for_terminal_execution(db, frontier=frontier)


@pytest.mark.asyncio
async def test_terminal_execution_allows_no_active_sibling_frontier() -> None:
    db = AsyncMock()
    result = SimpleNamespace(scalar_one_or_none=lambda: None)
    db.execute.return_value = result
    frontier = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), execution_id=uuid4())

    await _assert_no_active_sibling_frontiers_for_terminal_execution(db, frontier=frontier)
    db.execute.assert_awaited_once()
