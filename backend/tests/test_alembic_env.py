from unittest.mock import AsyncMock

import pytest

from app.core.alembic_compat import prepare_alembic_version_table


@pytest.mark.asyncio
async def test_prepare_alembic_version_table_widens_legacy_column():
    connection = AsyncMock()
    connection.scalar = AsyncMock(side_effect=[True, 32])

    await prepare_alembic_version_table(connection)

    connection.execute.assert_awaited_once()
    statement = str(connection.execute.await_args.args[0])
    assert "ALTER TABLE alembic_version" in statement
    assert "VARCHAR(64)" in statement


@pytest.mark.asyncio
async def test_prepare_alembic_version_table_is_noop_when_table_missing():
    connection = AsyncMock()
    connection.scalar = AsyncMock(return_value=False)

    await prepare_alembic_version_table(connection)

    connection.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_alembic_version_table_is_noop_when_column_is_already_wide():
    connection = AsyncMock()
    connection.scalar = AsyncMock(side_effect=[True, 64])

    await prepare_alembic_version_table(connection)

    connection.execute.assert_not_awaited()
