from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.workflow.transaction import commit_owned


@pytest.mark.asyncio
async def test_commit_owned_commits_only_when_service_owns_transaction() -> None:
    db = AsyncMock()

    await commit_owned(db, owned=True)

    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_commit_owned_does_not_commit_caller_owned_transaction() -> None:
    db = AsyncMock()

    await commit_owned(db, owned=False)

    db.commit.assert_not_awaited()
