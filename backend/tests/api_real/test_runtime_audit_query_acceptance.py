"""Phase 2.10-II Runtime Audit Query 的真实 PostgreSQL 验收。

职责：验证审计查询在真实 PostgreSQL 上的 tenant isolation、分页和运维过滤。
边界：不启动 API/Scheduler/Worker/PostgreSQL/Redis；测试租户与审计事实均自动创建并清理。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.infrastructure.db.session import SessionLocal
from app.models.core import Tenant
from app.models.runtime_operations import RuntimeOperationAudit
from app.services.runtime_operations.service import RuntimeOperationsService

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_runtime_audit_query_is_tenant_isolated_and_supports_operational_filters():
    """验证租户 A 不能看到租户 B，并验证动作/资源/结果/时间窗口组合过滤。"""
    suffix = uuid4().hex[:12]
    tenant_a, tenant_b = uuid4(), uuid4()
    now = datetime.utcnow().replace(microsecond=0)
    audit_ids = [uuid4() for _ in range(7)]

    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-audit-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-audit-b-{suffix}", status="active"),
                RuntimeOperationAudit(
                    id=audit_ids[0], tenant_id=tenant_a, actor="operator-a",
                    action="operator.workflow_execution.retry", resource_type="workflow_execution",
                    resource_id="exec-a-1", outcome="success", details={"fixture": suffix},
                    created_at=now - timedelta(minutes=5),
                ),
                RuntimeOperationAudit(
                    id=audit_ids[1], tenant_id=tenant_a, actor="operator-a",
                    action="operator.workflow_execution.cancel", resource_type="workflow_execution",
                    resource_id="exec-a-2", outcome="success", details={"fixture": suffix},
                    created_at=now - timedelta(minutes=4),
                ),
                RuntimeOperationAudit(
                    id=audit_ids[2], tenant_id=tenant_a, actor="operator-b",
                    action="operator.trigger.invoke", resource_type="trigger",
                    resource_id="trigger-a-1", outcome="rejected", details={"fixture": suffix},
                    created_at=now - timedelta(minutes=3),
                ),
                RuntimeOperationAudit(
                    id=audit_ids[3], tenant_id=tenant_a, actor="operator-a",
                    action="operator.workflow_execution.retry", resource_type="workflow_execution",
                    resource_id="exec-a-3", outcome="failed", details={"fixture": suffix},
                    created_at=now - timedelta(minutes=2),
                ),
                RuntimeOperationAudit(
                    id=audit_ids[4], tenant_id=tenant_a, actor="operator-a",
                    action="operator.workflow_execution.retry", resource_type="workflow_execution",
                    resource_id="exec-a-4", outcome="success", details={"fixture": suffix},
                    created_at=now - timedelta(minutes=1),
                ),
                RuntimeOperationAudit(
                    id=audit_ids[5], tenant_id=tenant_b, actor="operator-b",
                    action="operator.workflow_execution.retry", resource_type="workflow_execution",
                    resource_id="exec-b-1", outcome="success", details={"fixture": suffix},
                    created_at=now - timedelta(minutes=1),
                ),
                RuntimeOperationAudit(
                    id=audit_ids[6], tenant_id=tenant_b, actor="operator-b",
                    action="operator.trigger.invoke", resource_type="trigger",
                    resource_id="trigger-b-1", outcome="success", details={"fixture": suffix},
                    created_at=now,
                ),
            ])
            await db.commit()

        async with SessionLocal() as db:
            service = RuntimeOperationsService(db)

            page, page_size, total, rows = await service.audit_query(
                tenant_a, page=1, page_size=100,
            )
            assert (page, page_size, total) == (1, 100, 5)
            assert {row.tenant_id for row in rows} == {tenant_a}
            assert {row.id for row in rows} == set(audit_ids[:5])

            _, _, total, rows = await service.audit_query(
                tenant_a,
                page=1,
                page_size=10,
                action="operator.workflow_execution.retry",
                resource_type="workflow_execution",
                outcome="success",
            )
            assert total == 2
            assert [row.resource_id for row in rows] == ["exec-a-4", "exec-a-1"]

            _, _, total, rows = await service.audit_query(
                tenant_a,
                page=1,
                page_size=10,
                resource_id="exec-a-3",
            )
            assert total == 1
            assert rows[0].outcome == "failed"

            _, _, total, rows = await service.audit_query(
                tenant_a,
                page=1,
                page_size=10,
                since=now - timedelta(minutes=3, seconds=30),
                until=now - timedelta(minutes=1, seconds=30),
            )
            assert total == 2
            assert [row.resource_id for row in rows] == ["exec-a-3", "trigger-a-1"]

            _, _, total, rows = await service.audit_query(
                tenant_b, page=1, page_size=100,
            )
            assert total == 2
            assert {row.tenant_id for row in rows} == {tenant_b}

    finally:
        async with SessionLocal() as db:
            await db.execute(delete(RuntimeOperationAudit).where(RuntimeOperationAudit.id.in_(audit_ids)))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()
