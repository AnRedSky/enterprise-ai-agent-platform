"""Operator Action 结果资源类型 PostgreSQL 验收。"""

import pytest
from sqlalchemy import text

from app.infrastructure.db import engine


@pytest.mark.real_api
@pytest.mark.asyncio
async def test_operator_action_result_resource_type_schema_is_available() -> None:
    async with engine.begin() as connection:
        column = (
            await connection.execute(
                text(
                    """
                    SELECT data_type, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'operator_action_idempotencies'
                      AND column_name = 'result_resource_type'
                    """
                )
            )
        ).one_or_none()

        assert column is not None
        assert column.data_type == "character varying"
        assert column.character_maximum_length == 50

        index_names = {
            row[0]
            for row in (
                await connection.execute(
                    text(
                        """
                        SELECT indexname
                        FROM pg_indexes
                        WHERE schemaname = current_schema()
                          AND tablename = 'operator_action_idempotencies'
                        """
                    )
                )
            ).all()
        }

        assert "ix_operator_action_result_resource" in index_names
