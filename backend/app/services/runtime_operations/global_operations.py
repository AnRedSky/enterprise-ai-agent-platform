"""企业运行时全局运维视图。

本模块基于现有持久化 Workflow / Execution / Frontier / Trigger 事实提供只读、租户隔离的运行时视图，
不新增第二套生命周期、调度器或 Worker 状态机。

边界说明：
- WorkflowExecutionService 仍是执行生命周期的唯一权威入口。
- WorkflowTriggerService 仍是触发器生命周期的唯一权威入口。
- WorkflowFrontier 是 Worker 抢占事实的持久化来源。
- 当前没有持久化 Scheduler / Worker 心跳事实，因此进程存活状态只能报告为 ``unknown``，不能从活动事实推断。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.models.workflow_trigger import WorkflowTrigger


class GlobalRuntimeOperationsService:
    """基于规范化持久化事实构建只读的全局运行时运维视图。"""

    MAX_WINDOW_HOURS = 168
    MAX_ITEMS = 100
    _EXECUTION_STATUSES = ("pending", "running", "completed", "failed", "cancelled")

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @classmethod
    def _window(cls, window_hours: int) -> tuple[int, datetime]:
        bounded = min(max(window_hours, 1), cls.MAX_WINDOW_HOURS)
        return bounded, datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=bounded)

    @staticmethod
    def _counts(rows: list[tuple[str, int]]) -> dict[str, int]:
        return {status: int(count) for status, count in rows}

    @staticmethod
    def _agent_filter(agent_id: UUID | None):
        """按 WorkflowVersion.definition 中的规范 agent_id 字段筛选执行。

        参数:
            agent_id: 可选的 Agent 标识；为空时不增加筛选条件。

        返回:
            SQLAlchemy 表达式；为空输入返回 ``None``。

        说明:
            ``agent_id`` 是 WorkflowVersion.definition 的固定协议字段，不是独立 Agent
            生命周期表。这里使用固定 SQL 标识表达 JSON key，避免 PostgreSQL 编译时把
            ``agent_id`` 变成绑定参数，从而保持查询契约和 SQL 可观测性稳定；外部值仍
            通过 SQLAlchemy 绑定参数传入，不拼接用户输入。
        """
        if agent_id is None:
            return None
        return WorkflowExecution.workflow_version_id.in_(
            select(WorkflowVersion.id).where(
                WorkflowVersion.definition.op("->>")(literal_column("'agent_id'")) == str(agent_id),
            )
        )

    async def overview(
        self,
        tenant_id: UUID,
        *,
        window_hours: int = 24,
        workflow_id: UUID | None = None,
        agent_id: UUID | None = None,
        trigger_id: UUID | None = None,
        execution_id: UUID | None = None,
        execution_status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """返回租户的全局运行时状态。

        参数:
            tenant_id: 当前查询的租户边界。
            window_hours: 执行与 Worker frontier 的时间窗口，自动限制在 1~168 小时。
            workflow_id: 可选 Workflow 关联筛选。
            agent_id: 可选 Agent 关联筛选。
            trigger_id: 可选 Trigger 关联筛选。
            execution_id: 可选 Execution 关联筛选。
            execution_status: 可选执行状态筛选。
            limit: 最近执行明细最大返回数量，自动限制在 1~100。

        返回:
            包含 execution、workflow、trigger、worker、scheduler 状态以及过滤条件的只读快照。

        异常:
            当 ``execution_status`` 不属于规范执行状态集合时抛出 ``ValueError``。
        """
        window_hours, since = self._window(window_hours)
        limit = min(max(limit, 1), self.MAX_ITEMS)

        execution_filters = [
            WorkflowExecution.tenant_id == tenant_id,
            WorkflowExecution.created_at >= since,
        ]
        if workflow_id is not None:
            execution_filters.append(WorkflowExecution.workflow_id == workflow_id)
        agent_filter = self._agent_filter(agent_id)
        if agent_filter is not None:
            execution_filters.append(agent_filter)
        if execution_id is not None:
            execution_filters.append(WorkflowExecution.id == execution_id)
        if execution_status is not None:
            if execution_status not in self._EXECUTION_STATUSES:
                raise ValueError("unsupported execution_status")
            execution_filters.append(WorkflowExecution.status == execution_status)

        execution_rows = (await self.db.execute(
            select(WorkflowExecution.status, func.count())
            .where(*execution_filters)
            .group_by(WorkflowExecution.status)
        )).all()
        execution_counts = self._counts(execution_rows)

        workflow_filters = [Workflow.tenant_id == tenant_id]
        if workflow_id is not None:
            workflow_filters.append(Workflow.id == workflow_id)
        if agent_filter is not None:
            workflow_filters.append(
                Workflow.id.in_(select(WorkflowExecution.workflow_id).where(*execution_filters))
            )
        workflow_rows = (await self.db.execute(
            select(Workflow.status, func.count())
            .where(*workflow_filters)
            .group_by(Workflow.status)
        )).all()
        workflow_counts = self._counts(workflow_rows)

        trigger_filters = [WorkflowTrigger.tenant_id == tenant_id]
        if workflow_id is not None:
            trigger_filters.append(WorkflowTrigger.workflow_id == workflow_id)
        if trigger_id is not None:
            trigger_filters.append(WorkflowTrigger.id == trigger_id)
        trigger_rows = (await self.db.execute(
            select(WorkflowTrigger.status, func.count())
            .where(*trigger_filters)
            .group_by(WorkflowTrigger.status)
        )).all()
        trigger_counts = self._counts(trigger_rows)

        frontier_filters = [
            WorkflowFrontier.tenant_id == tenant_id,
            WorkflowFrontier.created_at >= since,
        ]
        if workflow_id is not None:
            frontier_filters.append(
                WorkflowFrontier.execution_id.in_(
                    select(WorkflowExecution.id).where(
                        WorkflowExecution.tenant_id == tenant_id,
                        WorkflowExecution.workflow_id == workflow_id,
                    )
                )
            )
        if agent_filter is not None:
            frontier_filters.append(
                WorkflowFrontier.execution_id.in_(select(WorkflowExecution.id).where(*execution_filters))
            )
        if execution_id is not None:
            frontier_filters.append(WorkflowFrontier.execution_id == execution_id)

        frontier_rows = (await self.db.execute(
            select(WorkflowFrontier.status, func.count())
            .where(*frontier_filters)
            .group_by(WorkflowFrontier.status)
        )).all()
        frontier_counts = self._counts(frontier_rows)

        now = datetime.now(UTC).replace(tzinfo=None)
        leased_count = await self.db.scalar(
            select(func.count()).select_from(WorkflowFrontier).where(
                *frontier_filters,
                WorkflowFrontier.worker_owner.is_not(None),
                WorkflowFrontier.worker_lease_expires_at.is_not(None),
                WorkflowFrontier.status == "running",
            )
        ) or 0
        expired_lease_count = await self.db.scalar(
            select(func.count()).select_from(WorkflowFrontier).where(
                *frontier_filters,
                WorkflowFrontier.worker_lease_expires_at.is_not(None),
                WorkflowFrontier.worker_lease_expires_at < now,
                WorkflowFrontier.status == "running",
            )
        ) or 0
        worker_owners = await self.db.scalar(
            select(func.count(func.distinct(WorkflowFrontier.worker_owner))).select_from(WorkflowFrontier).where(
                *frontier_filters,
                WorkflowFrontier.worker_owner.is_not(None),
                WorkflowFrontier.status == "running",
            )
        ) or 0

        scheduled_trigger_filters = [
            WorkflowTrigger.tenant_id == tenant_id,
            WorkflowTrigger.trigger_type == "schedule",
            WorkflowTrigger.status == "enabled",
        ]
        if workflow_id is not None:
            scheduled_trigger_filters.append(WorkflowTrigger.workflow_id == workflow_id)
        if trigger_id is not None:
            scheduled_trigger_filters.append(WorkflowTrigger.id == trigger_id)
        scheduled_enabled = await self.db.scalar(
            select(func.count()).select_from(WorkflowTrigger).where(*scheduled_trigger_filters)
        ) or 0

        recent_stmt = (
            select(WorkflowExecution, Workflow.name)
            .join(Workflow, Workflow.id == WorkflowExecution.workflow_id)
            .where(*execution_filters)
            .order_by(WorkflowExecution.created_at.desc(), WorkflowExecution.id.desc())
            .limit(limit)
        )
        recent_rows = (await self.db.execute(recent_stmt)).all()
        recent_executions = [
            {
                "id": execution.id,
                "workflow_id": execution.workflow_id,
                "workflow_name": workflow_name,
                "status": execution.status,
                "current_node_id": execution.current_node_id,
                "worker_owner": execution.worker_owner,
                "worker_attempt": execution.worker_attempt,
                "worker_lease_expires_at": execution.worker_lease_expires_at,
                "error_code": execution.error_code,
                "started_at": execution.started_at,
                "ended_at": execution.ended_at,
                "created_at": execution.created_at,
            }
            for execution, workflow_name in recent_rows
        ]

        active_execution_count = execution_counts.get("pending", 0) + execution_counts.get("running", 0)
        recovery_count = execution_counts.get("failed", 0)
        scheduler_backlog = frontier_counts.get("pending", 0)

        return {
            "window_hours": window_hours,
            "since": since,
            "generated_at": datetime.now(UTC),
            "filters": {
                "workflow_id": workflow_id,
                "agent_id": agent_id,
                "trigger_id": trigger_id,
                "execution_id": execution_id,
                "execution_status": execution_status,
            },
            "executions": {
                "total": sum(execution_counts.values()),
                "status_counts": execution_counts,
                "active_count": active_execution_count,
                "recovery_count": recovery_count,
                "items": recent_executions,
            },
            "workflows": {
                "total": sum(workflow_counts.values()),
                "status_counts": workflow_counts,
            },
            "triggers": {
                "total": sum(trigger_counts.values()),
                "status_counts": trigger_counts,
                "scheduled_enabled": int(scheduled_enabled),
            },
            "worker": {
                "liveness": "unknown",
                "liveness_reason_code": "NO_DURABLE_HEARTBEAT_FACT",
                "running_frontiers": frontier_counts.get("running", 0),
                "pending_frontiers": frontier_counts.get("pending", 0),
                "leased_frontiers": int(leased_count),
                "expired_leases": int(expired_lease_count),
                "active_worker_owners": int(worker_owners),
            },
            "scheduler": {
                "liveness": "unknown",
                "liveness_reason_code": "NO_DURABLE_HEARTBEAT_FACT",
                "enabled_scheduled_triggers": int(scheduled_enabled),
                "durable_frontier_backlog": int(scheduler_backlog),
            },
        }
