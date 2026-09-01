"""Operator Action → Audit → Result Resource 治理闭环的 PostgreSQL 验收。"""

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.infrastructure.db import engine


@pytest.mark.integration
@pytest.mark.asyncio
async def test_operator_action_audit_result_lineage_is_tenant_scoped() -> None:
    """验证 Operator Action、AuditLog 与结果资源能够形成同租户闭环。"""
    tenant_a, tenant_b = uuid4(), uuid4()
    user_a, user_b = uuid4(), uuid4()
    action_a, action_b = uuid4(), uuid4()
    audit_a, audit_b = uuid4(), uuid4()
    result_a, result_b = uuid4(), uuid4()

    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(
                text(
                    """
                    INSERT INTO tenants (id, name, status)
                    VALUES (:id, :name, 'active'), (:id_b, :name_b, 'active')
                    """
                ),
                {
                    "id": tenant_a,
                    "name": f"phase-210-lineage-a-{tenant_a.hex[:12]}",
                    "id_b": tenant_b,
                    "name_b": f"phase-210-lineage-b-{tenant_b.hex[:12]}",
                },
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO users (id, username, password_hash, tenant_id, status)
                    VALUES (:id, :username, 'fixture', :tenant_id, 'active'),
                           (:id_b, :username_b, 'fixture', :tenant_id_b, 'active')
                    """
                ),
                {
                    "id": user_a,
                    "username": f"phase-210-lineage-a-{user_a.hex[:12]}",
                    "tenant_id": tenant_a,
                    "id_b": user_b,
                    "username_b": f"phase-210-lineage-b-{user_b.hex[:12]}",
                    "tenant_id_b": tenant_b,
                },
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO operator_action_idempotencies
                    (id, tenant_id, actor_id, resource_type, resource_id, action,
                     idempotency_key, status, result_resource_type, result_resource_id)
                    VALUES
                    (:id, :tenant_id, :actor_id, 'workflow_execution', :resource_id, 'retry',
                     :idempotency_key, 'succeeded', 'workflow_execution', :result_resource_id),
                    (:id_b, :tenant_id_b, :actor_id_b, 'workflow_execution', :resource_id_b, 'retry',
                     :idempotency_key_b, 'succeeded', 'workflow_execution', :result_resource_id_b)
                    """
                ),
                {
                    "id": action_a,
                    "tenant_id": tenant_a,
                    "actor_id": user_a,
                    "resource_id": result_a,
                    "idempotency_key": f"phase-210-lineage-a-{action_a.hex}",
                    "result_resource_id": result_a,
                    "id_b": action_b,
                    "tenant_id_b": tenant_b,
                    "actor_id_b": user_b,
                    "resource_id_b": result_b,
                    "idempotency_key_b": f"phase-210-lineage-b-{action_b.hex}",
                    "result_resource_id_b": result_b,
                },
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO audit_logs
                    (id, actor_id, tenant_id, workflow_execution_id, operator_action_id,
                     action, resource_type, resource_id, trace_id, status, metadata)
                    VALUES
                    (:id, :actor_id, :tenant_id, NULL, :operator_action_id,
                     'operator.workflow_execution.retry', 'workflow_execution', :resource_id,
                     :trace_id, 'success', :metadata),
                    (:id_b, :actor_id_b, :tenant_id_b, NULL, :operator_action_id_b,
                     'operator.workflow_execution.retry', 'workflow_execution', :resource_id_b,
                     :trace_id_b, 'success', :metadata_b)
                    """
                ),
                {
                    "id": audit_a,
                    "actor_id": user_a,
                    "tenant_id": tenant_a,
                    "operator_action_id": action_a,
                    "resource_id": str(result_a),
                    "trace_id": str(result_a),
                    "metadata": '{"fixture": "lineage-a"}',
                    "id_b": audit_b,
                    "actor_id_b": user_b,
                    "tenant_id_b": tenant_b,
                    "operator_action_id_b": action_b,
                    "resource_id_b": str(result_b),
                    "trace_id_b": str(result_b),
                    "metadata_b": '{"fixture": "lineage-b"}',
                },
            )

            rows = (
                await connection.execute(
                    text(
                        """
                        SELECT a.operator_action_id, o.result_resource_type, o.result_resource_id
                        FROM audit_logs a
                        JOIN operator_action_idempotencies o
                          ON o.id = a.operator_action_id
                         AND o.tenant_id = a.tenant_id
                        WHERE a.tenant_id = :tenant_id
                          AND a.id = :audit_id
                        """
                    ),
                    {"tenant_id": tenant_a, "audit_id": audit_a},
                )
            ).all()
            assert rows == [(action_a, "workflow_execution", result_a)]

            cross_tenant = (
                await connection.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM audit_logs a
                        JOIN operator_action_idempotencies o ON o.id = a.operator_action_id
                        WHERE a.tenant_id = :tenant_id
                          AND o.tenant_id <> :tenant_id
                        """
                    ),
                    {"tenant_id": tenant_a},
                )
            ).scalar_one()
            assert cross_tenant == 0
        finally:
            await transaction.rollback()
