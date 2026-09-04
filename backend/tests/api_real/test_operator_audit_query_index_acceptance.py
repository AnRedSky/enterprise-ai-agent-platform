"""Canonical Operator Audit 查询索引的 PostgreSQL 验收。

职责：验证 AuditLog 唯一事实源上的 Operator Audit 查询复合索引已经按租户优先和过滤维度正确落库。
边界：只检查 PostgreSQL 系统目录中的索引事实，不修改业务数据，不启动任何服务。
关键依赖：PostgreSQL、SQLAlchemy AsyncEngine。
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

import pytest

from app.core.config import settings


EXPECTED_INDEXES = {
    "ix_operator_audit_tenant_action_created": ("tenant_id", "action", "created_at"),
    "ix_operator_audit_tenant_actor_created": ("tenant_id", "actor_id", "created_at"),
    "ix_operator_audit_tenant_resource_created": (
        "tenant_id",
        "resource_type",
        "resource_id",
        "created_at",
    ),
    "ix_operator_audit_tenant_execution_created": (
        "tenant_id",
        "workflow_execution_id",
        "created_at",
    ),
    "ix_operator_audit_tenant_trace_created": ("tenant_id", "trace_id", "created_at"),
    "ix_operator_audit_tenant_operator_action_created": (
        "tenant_id",
        "operator_action_id",
        "created_at",
    ),
}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_canonical_operator_audit_indexes_are_tenant_scoped_and_ordered() -> None:
    """验证 Canonical Operator Audit 的所有正式查询索引存在且列顺序满足查询契约。"""
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool, pool_pre_ping=True)
    try:
        async with test_engine.connect() as connection:
            rows = (
                await connection.execute(
                    text(
                        """
                        SELECT indexname, indexdef
                        FROM pg_indexes
                        WHERE schemaname = current_schema()
                          AND tablename = 'audit_logs'
                          AND indexname = ANY(:index_names)
                        ORDER BY indexname
                        """
                    ),
                    {"index_names": list(EXPECTED_INDEXES)},
                )
            ).all()

            definitions = {name: definition for name, definition in rows}
            assert set(definitions) == set(EXPECTED_INDEXES)

            for index_name, columns in EXPECTED_INDEXES.items():
                expected_columns = ", ".join(columns)
                assert f"({expected_columns})" in definitions[index_name]
    finally:
        await test_engine.dispose()
