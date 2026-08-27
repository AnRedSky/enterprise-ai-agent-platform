"""Durable Recovery trace lineage link。

职责：把 Automatic Recovery 创建的 trace_id 持久化关联到 Resume Execution，
使独立 Worker 后续可以从 WorkflowTraceEvent 恢复同一条 Recovery trace。
边界：不创建新的 Trace/Telemetry SDK，不修改业务 input_data；只复用已有 WorkflowTraceEvent 治理事实。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_trace import WorkflowTraceEvent


class WorkflowRecoveryTraceLinkService:
    """持久化 Recovery → Resume Execution 的 trace lineage。"""

    EVENT_TYPE = "recovery.trace_linked"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def link(
        self,
        source_execution: WorkflowExecution,
        resume_execution: WorkflowExecution,
        trace_id: str,
        actor_id: UUID | None,
    ) -> WorkflowTraceEvent:
        """为 Resume Execution 建立可持久化的 Recovery trace 关联。

        同一 Resume Execution + trace_id 幂等命中时直接返回已有事件，避免 Scheduler/Recovery
        重试造成重复 lineage 记录。事件只保存身份与关联信息，不保存 Checkpoint state_data。
        """
        existing = (
            await self.db.execute(
                select(WorkflowTraceEvent)
                .where(
                    WorkflowTraceEvent.execution_id == resume_execution.id,
                    WorkflowTraceEvent.tenant_id == resume_execution.tenant_id,
                    WorkflowTraceEvent.event_type == self.EVENT_TYPE,
                    WorkflowTraceEvent.trace_id == trace_id,
                )
                .order_by(WorkflowTraceEvent.created_at.asc(), WorkflowTraceEvent.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        event = WorkflowTraceEvent(
            tenant_id=resume_execution.tenant_id,
            execution_id=resume_execution.id,
            workflow_id=resume_execution.workflow_id,
            workflow_version_id=resume_execution.workflow_version_id,
            event_type=self.EVENT_TYPE,
            status=resume_execution.status,
            trace_id=trace_id,
            actor_id=actor_id,
            data={
                "source_execution_id": str(source_execution.id),
                "resume_execution_id": str(resume_execution.id),
                "phase": "automatic_recovery",
            },
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_trace_id(self, resume_execution: WorkflowExecution) -> str | None:
        """从持久化 Recovery lineage 恢复 Resume Execution 对应的 trace_id。

        该查询只读取 trace identity，不读取或返回业务 payload，使独立 Worker 可以在
        接管 Resume Execution 后继续原 Recovery trace。若没有 lineage，返回 None。
        """
        result = await self.db.execute(
            select(WorkflowTraceEvent.trace_id)
            .where(
                WorkflowTraceEvent.execution_id == resume_execution.id,
                WorkflowTraceEvent.tenant_id == resume_execution.tenant_id,
                WorkflowTraceEvent.event_type == self.EVENT_TYPE,
            )
            .order_by(WorkflowTraceEvent.created_at.asc(), WorkflowTraceEvent.id.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()
