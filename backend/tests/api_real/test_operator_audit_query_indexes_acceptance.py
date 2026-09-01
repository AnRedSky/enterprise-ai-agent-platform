"""Operator Audit 查询索引 PostgreSQL 真实验收。"""

import pytest
from sqlalchemy import text

from app.infrastructure.db import engine


EXPECTED_INDEXES = {
    "ix_operator_audit_tenant_action_created": ["tenant_id", "action", "created_at"],
    "ix_operator_audit_tenant_actor_created": ["tenant_id", "actor_id", "created_at"],
    "ix_operator_audit_tenant_resource_created": ["tenant_id", "resource_type", "resource_id", "created_at"],
    "ix_operator_audit_tenant_execution_created": ["tenant_id", "workflow_execution_id", "created_at"],
    "ix_operator_audit_tenant_trace_created": ["tenant_id", "trace_id", "created_at"],
}


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.asyncio
async def test_operator_audit_query_indexes_target_canonical_audit_log() -> None:
    """验证 Operator Audit 查询索引全部建立在 AuditLog 唯一事实源上。"""
    async with engine.connect() as connection:
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = current_schema()
                      AND tablename = 'audit_logs'
                    """
                )
            )
        ).all()

    indexes = {row.indexname: row.indexdef for row in rows}
    for index_name, columns in EXPECTED_INDEXES.items():
        assert index_name in indexes
        definition = indexes[index_name]
        assert all(f'"{column}"' in definition for column in columns)


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.asyncio
async def test_operator_audit_query_indexes_preserve_tenant_first_boundary() -> None:
    """验证 Operator Audit 复合索引均以 tenant_id 作为首列，避免跨租户查询优化失去边界。"""
    async with engine.connect() as connection:
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = current_schema()
                      AND tablename = 'audit_logs'
                      AND indexname LIKE 'ix_operator_audit_%'
                    """
                )
            )
        ).all()

    for row in rows:
        if row.indexname in EXPECTED_INDEXES:
            assert row.indexdef.index('"tenant_id"') < row.indexdef.index('"' + EXPECTED_INDEXES[row.indexname][1] + '"')
