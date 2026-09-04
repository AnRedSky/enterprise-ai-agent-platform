"""Canonical Operator Audit 查询路径的 PostgreSQL 性能验收。

职责：验证 Operator Audit 查询在 tenant-scoped 过滤下能够使用对应 Canonical 复合索引，防止查询代码与数据库优化结构发生漂移。
边界：只验证 PostgreSQL 查询计划，不启动任何服务、不写入业务数据，也不建立第二套审计事实源。
关键依赖：PostgreSQL、SQLAlchemy AsyncEngine、Canonical audit_logs 索引。
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings


pytestmark = pytest.mark.integration

TENANT_ID = "00000000-0000-0000-0000-000000000001"
ACTOR_ID = "00000000-0000-0000-0000-000000000002"
OPERATOR_ACTION_ID = "00000000-0000-0000-0000-000000000003"
WORKFLOW_EXECUTION_ID = "00000000-0000-0000-0000-000000000004"


QUERY_CASES = (
    (
        "action",
        "ix_operator_audit_tenant_action_created",
        """
        SELECT id
        FROM audit_logs
        WHERE tenant_id = :tenant_id
          AND action = :action
          AND created_at >= :since
        ORDER BY created_at DESC, id DESC
        LIMIT 50
        """,
        {
            "action": "operator.workflow_execution.retry",
            "since": "2026-01-01T00:00:00+00:00",
        },
    ),
    (
        "actor",
        "ix_operator_audit_tenant_actor_created",
        """
        SELECT id
        FROM audit_logs
        WHERE tenant_id = :tenant_id
          AND actor_id = :actor_id
        ORDER BY created_at DESC, id DESC
        LIMIT 50
        """,
        {"actor_id": ACTOR_ID},
    ),
    (
        "resource",
        "ix_operator_audit_tenant_resource_created",
        """
        SELECT id
        FROM audit_logs
        WHERE tenant_id = :tenant_id
          AND resource_type = :resource_type
          AND resource_id = :resource_id
        ORDER BY created_at DESC, id DESC
        LIMIT 50
        """,
        {"resource_type": "workflow_execution", "resource_id": WORKFLOW_EXECUTION_ID},
    ),
    (
        "execution",
        "ix_operator_audit_tenant_execution_created",
        """
        SELECT id
        FROM audit_logs
        WHERE tenant_id = :tenant_id
          AND workflow_execution_id = :workflow_execution_id
        ORDER BY created_at DESC, id DESC
        LIMIT 50
        """,
        {"workflow_execution_id": WORKFLOW_EXECUTION_ID},
    ),
    (
        "trace",
        "ix_operator_audit_tenant_trace_created",
        """
        SELECT id
        FROM audit_logs
        WHERE tenant_id = :tenant_id
          AND trace_id = :trace_id
        ORDER BY created_at DESC, id DESC
        LIMIT 50
        """,
        {"trace_id": "operator-trace-performance-gate"},
    ),
    (
        "operator_action",
        "ix_operator_audit_tenant_operator_action_created",
        """
        SELECT id
        FROM audit_logs
        WHERE tenant_id = :tenant_id
          AND operator_action_id = :operator_action_id
        ORDER BY created_at DESC, id DESC
        LIMIT 50
        """,
        {"operator_action_id": OPERATOR_ACTION_ID},
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize("case_name,index_name,query,parameters", QUERY_CASES)
async def test_operator_audit_query_uses_canonical_tenant_scoped_index(
    case_name: str,
    index_name: str,
    query: str,
    parameters: dict[str, str],
) -> None:
    """验证每条正式 Operator Audit 过滤路径都可命中对应 tenant-first 复合索引。"""
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool, pool_pre_ping=True)
    try:
        async with test_engine.connect() as connection:
            async with connection.begin():
                await connection.execute(text("SET LOCAL enable_seqscan = off"))
                plan_rows = (
                    await connection.execute(
                        text(f"EXPLAIN (COSTS OFF) {query}"),
                        {"tenant_id": TENANT_ID, **parameters},
                    )
                ).scalars().all()

        plan = "\n".join(str(row) for row in plan_rows)
        assert index_name in plan, f"{case_name} 查询未使用 Canonical index {index_name}:\n{plan}"
    finally:
        await test_engine.dispose()
