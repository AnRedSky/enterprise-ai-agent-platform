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


async def _load_operator_audit_index_columns(connection) -> dict[str, list[str]]:
    """读取 PostgreSQL 索引实际列顺序，而不是解析数据库生成的 DDL 文本。

    Args:
        connection: 当前 PostgreSQL 异步连接。

    Returns:
        dict[str, list[str]]: 索引名称到实际索引键列顺序的映射。

    设计意图：pg_indexes.indexdef 是数据库生成的展示文本，未必对普通标识符保留双引号；
    验收应断言 PostgreSQL 的真实索引元数据，避免把引用格式误判为 schema 漂移。
    """
    rows = (
        await connection.execute(
            text(
                """
                SELECT index_name, column_name
                FROM (
                    SELECT
                        index_class.relname AS index_name,
                        attribute.attname AS column_name,
                        index_column.ordinality AS ordinal_position
                    FROM pg_class AS table_class
                    JOIN pg_namespace AS table_namespace
                      ON table_namespace.oid = table_class.relnamespace
                    JOIN pg_index AS index_metadata
                      ON index_metadata.indrelid = table_class.oid
                    JOIN pg_class AS index_class
                      ON index_class.oid = index_metadata.indexrelid
                    CROSS JOIN LATERAL unnest(index_metadata.indkey)
                        WITH ORDINALITY AS index_column(attnum, ordinality)
                    JOIN pg_attribute AS attribute
                      ON attribute.attrelid = table_class.oid
                     AND attribute.attnum = index_column.attnum
                    WHERE table_namespace.nspname = current_schema()
                      AND table_class.relname = 'audit_logs'
                      AND index_class.relname LIKE 'ix_operator_audit_%'
                ) AS index_columns
                ORDER BY index_name, ordinal_position
                """
            )
        )
    ).all()
    indexes: dict[str, list[str]] = {}
    for row in rows:
        indexes.setdefault(row.index_name, []).append(row.column_name)
    return indexes


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.asyncio
async def test_operator_audit_query_indexes_target_canonical_audit_log() -> None:
    """验证 Operator Audit 查询索引全部建立在 AuditLog 唯一事实源上。"""
    async with engine.connect() as connection:
        indexes = await _load_operator_audit_index_columns(connection)

    for index_name, columns in EXPECTED_INDEXES.items():
        assert indexes.get(index_name) == columns


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.asyncio
async def test_operator_audit_query_indexes_preserve_tenant_first_boundary() -> None:
    """验证 Operator Audit 复合索引均以 tenant_id 作为首列，避免跨租户查询优化失去边界。"""
    async with engine.connect() as connection:
        indexes = await _load_operator_audit_index_columns(connection)

    for index_name in EXPECTED_INDEXES:
        assert indexes[index_name][0] == "tenant_id"
