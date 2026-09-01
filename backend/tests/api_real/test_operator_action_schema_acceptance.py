"""Operator Action → Audit → Result Resource 数据库契约的 PostgreSQL 验收。"""

import pytest
from sqlalchemy import text

from app.infrastructure.db import engine


@pytest.mark.integration
@pytest.mark.asyncio
async def test_operator_action_governance_schema_is_migration_complete() -> None:
    """验证 Operator Action 治理闭环所需列、外键和唯一 head 依赖已落到 PostgreSQL。"""
    async with engine.connect() as connection:
        columns = (
            await connection.execute(
                text(
                    """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND (
                          (table_name = 'audit_logs' AND column_name = 'operator_action_id')
                          OR (
                              table_name = 'operator_action_idempotencies'
                              AND column_name = 'result_resource_type'
                          )
                      )
                    ORDER BY table_name, column_name
                    """
                )
            )
        ).all()
        assert columns == [
            ("audit_logs", "operator_action_id"),
            ("operator_action_idempotencies", "result_resource_type"),
        ]

        foreign_key = (
            await connection.execute(
                text(
                    """
                    SELECT kcu.column_name, ccu.table_name, ccu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON kcu.constraint_name = tc.constraint_name
                     AND kcu.table_schema = tc.table_schema
                    JOIN information_schema.constraint_column_usage ccu
                      ON ccu.constraint_name = tc.constraint_name
                     AND ccu.table_schema = tc.table_schema
                    WHERE tc.table_schema = 'public'
                      AND tc.table_name = 'audit_logs'
                      AND tc.constraint_type = 'FOREIGN KEY'
                      AND kcu.column_name = 'operator_action_id'
                    """
                )
            )
        ).one()
        assert foreign_key == (
            "operator_action_id",
            "operator_action_idempotencies",
            "id",
        )

        index_columns = (
            await connection.execute(
                text(
                    """
                    SELECT indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = 'audit_logs'
                      AND indexname = 'ix_operator_audit_tenant_operator_action_created'
                    """
                )
            ).scalar_one()
        )
        assert '(tenant_id, operator_action_id, created_at)' in index_columns
