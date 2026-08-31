"""企业运行时 Worker / Scheduler 诊断查询。

职责：只读聚合现有 WorkflowFrontier 与 WorkflowTrigger 持久化事实，提供租户隔离的
Worker claim / lease 诊断和 Scheduler durable posture。
边界：不创建心跳事实、不修改 Frontier / Execution / Trigger 状态，也不推断不存在的
进程存活状态；Worker owner 仅表示持久化 claim 事实，Scheduler loop 仅在存在持久化事实
时才允许报告状态。
关键依赖：SQLAlchemy AsyncSession、WorkflowFrontier、WorkflowTrigger。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowFrontier
from app.models.workflow_trigger import WorkflowTrigger


class RuntimeDiagnosticsService:
    """基于规范化 Durable Facts 构建只读的 Worker / Scheduler 诊断快照。"""

    MAX_WINDOW_HOURS = 168
    MAX_ITEMS = 100

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @classmethod
    def _since(cls, window_hours: int) -> tuple[int, datetime]:
        """生成诊断时间窗口。

        参数:
            window_hours: 查询窗口小时数。

        返回:
            规范化后的窗口小时数和无时区 UTC 起始时间。
        """
        bounded = min(max(window_hours, 1), cls.MAX_WINDOW_HOURS)
        return bounded, datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=bounded)

    async def worker(self, tenant_id: UUID, *, window_hours: int = 24, limit: int = 50) -> dict[str, Any]:
        """返回租户 Worker claim、lease、并发 owner 与失败诊断。

        参数:
            tenant_id: 当前认证租户。
            window_hours: Durable Frontier 查询窗口，限制为 1~168 小时。
            limit: owner 明细最大数量，限制为 1~100。

        返回:
            包含 claim 状态、lease 状态、owner 统计及最近异常 Frontier 的诊断快照。

        说明:
            `worker_owner` 是抢占事实而非进程身份。没有 durable heartbeat 时，进程
            liveness 必须保持 unknown，不能依据最近 claim 活动伪造 healthy。
        """
        window_hours, since = self._since(window_hours)
        limit = min(max(limit, 1), self.MAX_ITEMS)
        base = [
            WorkflowFrontier.tenant_id == tenant_id,
            WorkflowFrontier.created_at >= since,
        ]
        now = datetime.now(UTC).replace(tzinfo=None)

        status_rows = (await self.db.execute(
            select(WorkflowFrontier.status, func.count())
            .where(*base)
            .group_by(WorkflowFrontier.status)
        )).all()
        status_counts = {status: int(count) for status, count in status_rows}

        lease_rows = (await self.db.execute(
            select(
                func.count().filter(WorkflowFrontier.worker_lease_expires_at.is_(None)),
                func.count().filter(
                    WorkflowFrontier.worker_lease_expires_at.is_not(None),
                    WorkflowFrontier.worker_lease_expires_at >= now,
                ),
                func.count().filter(
                    WorkflowFrontier.worker_lease_expires_at.is_not(None),
                    WorkflowFrontier.worker_lease_expires_at < now,
                ),
            ).select_from(WorkflowFrontier).where(*base)
        )).one()

        owner_rows = (await self.db.execute(
            select(WorkflowFrontier.worker_owner, func.count())
            .where(*base, WorkflowFrontier.worker_owner.is_not(None))
            .group_by(WorkflowFrontier.worker_owner)
            .order_by(func.count().desc(), WorkflowFrontier.worker_owner.asc())
            .limit(limit)
        )).all()

        error_rows = (await self.db.execute(
            select(
                WorkflowFrontier.id,
                WorkflowFrontier.execution_id,
                WorkflowFrontier.status,
                WorkflowFrontier.attempt,
                WorkflowFrontier.worker_owner,
                WorkflowFrontier.worker_lease_expires_at,
                WorkflowFrontier.error_code,
                WorkflowFrontier.created_at,
            )
            .where(*base, WorkflowFrontier.error_code.is_not(None))
            .order_by(WorkflowFrontier.created_at.desc(), WorkflowFrontier.id.desc())
            .limit(limit)
        )).all()

        return {
            "window_hours": window_hours,
            "generated_at": datetime.now(UTC),
            "liveness": "unknown",
            "liveness_reason_code": "NO_DURABLE_HEARTBEAT_FACT",
            "frontier": {
                "total": sum(status_counts.values()),
                "status_counts": status_counts,
                "running": status_counts.get("running", 0),
                "pending": status_counts.get("pending", 0),
                "completed": status_counts.get("completed", 0),
                "failed": status_counts.get("failed", 0),
            },
            "leases": {
                "without_expiry": int(lease_rows[0]),
                "active": int(lease_rows[1]),
                "expired": int(lease_rows[2]),
            },
            "owners": [
                {"worker_owner": owner, "claim_count": int(count)}
                for owner, count in owner_rows
            ],
            "recent_errors": [
                {
                    "id": row.id,
                    "execution_id": row.execution_id,
                    "status": row.status,
                    "attempt": row.attempt,
                    "worker_owner": row.worker_owner,
                    "worker_lease_expires_at": row.worker_lease_expires_at,
                    "error_code": row.error_code,
                    "created_at": row.created_at,
                }
                for row in error_rows
            ],
        }

    async def scheduler(self, tenant_id: UUID, *, limit: int = 50) -> dict[str, Any]:
        """返回 Scheduler 可由 Durable Facts 证明的 backlog 与触发器状态。

        参数:
            tenant_id: 当前认证租户。
            limit: 最近 scheduled trigger 明细最大数量，限制为 1~100。

        返回:
            Scheduler durable posture。当前没有 Scheduler heartbeat，因此 liveness 为 unknown。
        """
        limit = min(max(limit, 1), self.MAX_ITEMS)
        enabled = await self.db.scalar(
            select(func.count()).select_from(WorkflowTrigger).where(
                WorkflowTrigger.tenant_id == tenant_id,
                WorkflowTrigger.trigger_type == "schedule",
                WorkflowTrigger.status == "enabled",
            )
        ) or 0
        disabled = await self.db.scalar(
            select(func.count()).select_from(WorkflowTrigger).where(
                WorkflowTrigger.tenant_id == tenant_id,
                WorkflowTrigger.trigger_type == "schedule",
                WorkflowTrigger.status != "enabled",
            )
        ) or 0
        frontier_pending = await self.db.scalar(
            select(func.count()).select_from(WorkflowFrontier).where(
                WorkflowFrontier.tenant_id == tenant_id,
                WorkflowFrontier.status == "pending",
            )
        ) or 0
        triggers = (await self.db.execute(
            select(WorkflowTrigger.id, WorkflowTrigger.workflow_id, WorkflowTrigger.name,
                   WorkflowTrigger.status, WorkflowTrigger.config, WorkflowTrigger.updated_at)
            .where(
                WorkflowTrigger.tenant_id == tenant_id,
                WorkflowTrigger.trigger_type == "schedule",
            )
            .order_by(WorkflowTrigger.updated_at.desc(), WorkflowTrigger.id.desc())
            .limit(limit)
        )).all()

        return {
            "generated_at": datetime.now(UTC),
            "liveness": "unknown",
            "liveness_reason_code": "NO_DURABLE_HEARTBEAT_FACT",
            "durable": {
                "enabled_scheduled_triggers": int(enabled),
                "disabled_scheduled_triggers": int(disabled),
                "pending_frontier_items": int(frontier_pending),
            },
            "triggers": [
                {
                    "id": row.id,
                    "workflow_id": row.workflow_id,
                    "name": row.name,
                    "status": row.status,
                    "config": row.config,
                    "updated_at": row.updated_at,
                }
                for row in triggers
            ],
        }
