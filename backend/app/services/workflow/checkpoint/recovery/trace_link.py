"""Durable Recovery trace lineage link。

职责：把 Automatic Recovery 创建的 trace_id 持久化关联到 Resume Execution，并验证 Source、Resume、Checkpoint 与已有 Trace 之间的同一条 lineage。
边界：不创建新的 Trace/Telemetry SDK，不修改业务 input_data；只复用已有 WorkflowTraceEvent 治理事实。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_trace import WorkflowTraceEvent


class WorkflowRecoveryTraceLinkService:
    """持久化并校验 Recovery → Resume Execution 的 trace lineage。"""

    EVENT_TYPE = "recovery.trace_linked"
    DAG_DECISION_EVENT = "workflow.dag.frontier_decided"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _assert_resume_checkpoint_lineage(self, source_execution: WorkflowExecution, resume_execution: WorkflowExecution) -> int:
        if resume_execution.resume_of_execution_id != source_execution.id:
            raise ValueError("Recovery trace lineage 的 Resume Execution 必须指向 Source Execution")
        if resume_execution.tenant_id != source_execution.tenant_id:
            raise ValueError("Recovery trace lineage 不允许跨 tenant 建立 Source/Resume 关联")
        if resume_execution.workflow_version_id != source_execution.workflow_version_id:
            raise ValueError("Recovery trace lineage 不允许跨 workflow version 建立 Source/Resume 关联")
        checkpoint_sequence = resume_execution.resume_checkpoint_sequence
        if checkpoint_sequence is None:
            raise ValueError("Recovery trace lineage 缺少 resume_checkpoint_sequence")
        checkpoint = (
            await self.db.execute(
                select(WorkflowExecutionCheckpoint.sequence)
                .where(
                    WorkflowExecutionCheckpoint.execution_id == source_execution.id,
                    WorkflowExecutionCheckpoint.sequence == checkpoint_sequence,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if checkpoint is None:
            raise ValueError("Recovery trace lineage 的 resume_checkpoint_sequence 不存在于 Source Execution")
        return checkpoint

    @staticmethod
    def _assert_existing_lineage_event(event: WorkflowTraceEvent, source_execution: WorkflowExecution, resume_execution: WorkflowExecution, checkpoint_sequence: int) -> None:
        data = event.data if isinstance(event.data, dict) else {}
        expected = {
            "source_execution_id": str(source_execution.id),
            "resume_execution_id": str(resume_execution.id),
            "resume_checkpoint_sequence": checkpoint_sequence,
        }
        for key, value in expected.items():
            if data.get(key) != value:
                raise ValueError(f"Recovery trace lineage 已存在但 {key} 不一致")

    @staticmethod
    def _assert_existing_dag_decision(
        event: WorkflowTraceEvent,
        decision_id: str,
        completed_node_ids: list[str],
        frontier_node_ids: list[str],
        selected_predecessors: list[dict[str, object]],
    ) -> None:
        """校验已有 Decision event，避免幂等命中掩盖历史 Decision payload 漂移。"""
        data = event.data if isinstance(event.data, dict) else {}
        expected = {
            "decision_id": decision_id,
            "completed_node_ids": completed_node_ids,
            "frontier_node_ids": frontier_node_ids,
            "selected_predecessors": selected_predecessors,
        }
        for key, value in expected.items():
            if data.get(key) != value:
                raise ValueError(f"DAG Decision Trace 已存在但 {key} 不一致")

    async def link(
        self,
        source_execution: WorkflowExecution,
        resume_execution: WorkflowExecution,
        trace_id: str,
        actor_id: UUID | None,
        *,
        commit: bool = True,
    ) -> WorkflowTraceEvent:
        """建立 Recovery → Resume trace lineage。

        Args:
            source_execution: 失败且作为恢复来源的 Execution。
            resume_execution: 已完成 Resume Bootstrap 的目标 Execution。
            trace_id: 本次自动恢复的 trace 标识。
            actor_id: 触发恢复的操作者身份。
            commit: 是否由本方法提交事务；自动恢复主事务传入 False，统一由上层提交。

        Returns:
            WorkflowTraceEvent: 已存在或新建的 trace lineage 事件。

        Raises:
            ValueError: Source、Resume、Checkpoint lineage 不一致时拒绝写入。

        事务边界：commit=False 时只 flush 不 commit，使 trace lineage 与 Resume、Node lineage、Frontier 在同一事务提交。
        """
        checkpoint_sequence = await self._assert_resume_checkpoint_lineage(source_execution, resume_execution)
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
            self._assert_existing_lineage_event(existing, source_execution, resume_execution, checkpoint_sequence)
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
                "resume_checkpoint_sequence": checkpoint_sequence,
                "phase": "automatic_recovery",
            },
        )
        self.db.add(event)
        await self.db.flush()
        if commit:
            await self.db.commit()
            await self.db.refresh(event)
        return event

    async def assert_dag_decision_replay_consistent(
        self,
        execution: WorkflowExecution,
        trace_id: str,
        completed_node_ids: list[str],
        decision_fingerprint: str,
        frontier_node_ids: list[str] | None = None,
        selected_predecessors: list[dict[str, object]] | None = None,
    ) -> None:
        result = await self.db.execute(
            select(WorkflowTraceEvent.data)
            .where(
                WorkflowTraceEvent.tenant_id == execution.tenant_id,
                WorkflowTraceEvent.workflow_version_id == execution.workflow_version_id,
                WorkflowTraceEvent.trace_id == trace_id,
                WorkflowTraceEvent.event_type == self.DAG_DECISION_EVENT,
            )
            .order_by(WorkflowTraceEvent.created_at.asc(), WorkflowTraceEvent.id.asc())
        )
        for data in result.scalars().all():
            if not isinstance(data, dict):
                continue
            previous_completed = data.get("completed_node_ids")
            previous_fingerprint = data.get("decision_id")
            if previous_completed != completed_node_ids:
                continue
            if previous_fingerprint and previous_fingerprint != decision_fingerprint:
                raise ValueError("DAG Recovery Decision fingerprint 不一致：同一 durable completed facts 产生了不同 Decision")
            if frontier_node_ids is not None and data.get("frontier_node_ids") != frontier_node_ids:
                raise ValueError("DAG Recovery Decision frontier 不一致：同一 durable completed facts 产生了不同 frontier")
            if selected_predecessors is not None and data.get("selected_predecessors") != selected_predecessors:
                raise ValueError("DAG Recovery Decision predecessor 不一致：同一 durable completed facts 产生了不同 predecessor selection")

    async def record_dag_decision(
        self,
        execution: WorkflowExecution,
        trace_id: str | None,
        actor_id: UUID | None,
        decision_id: str,
        completed_node_ids: list[str],
        frontier_node_ids: list[str],
        selected_predecessors: list[dict[str, object]],
    ) -> WorkflowTraceEvent | None:
        if not trace_id:
            return None

        existing = (
            await self.db.execute(
                select(WorkflowTraceEvent)
                .where(
                    WorkflowTraceEvent.execution_id == execution.id,
                    WorkflowTraceEvent.tenant_id == execution.tenant_id,
                    WorkflowTraceEvent.workflow_version_id == execution.workflow_version_id,
                    WorkflowTraceEvent.trace_id == trace_id,
                    WorkflowTraceEvent.event_type == self.DAG_DECISION_EVENT,
                    WorkflowTraceEvent.data["decision_id"].as_string() == decision_id,
                )
                .order_by(WorkflowTraceEvent.created_at.asc(), WorkflowTraceEvent.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            self._assert_existing_dag_decision(
                existing,
                decision_id,
                completed_node_ids,
                frontier_node_ids,
                selected_predecessors,
            )
            return existing

        event = WorkflowTraceEvent(
            tenant_id=execution.tenant_id,
            execution_id=execution.id,
            workflow_id=execution.workflow_id,
            workflow_version_id=execution.workflow_version_id,
            event_type=self.DAG_DECISION_EVENT,
            status=execution.status,
            trace_id=trace_id,
            actor_id=actor_id,
            data={
                "decision_id": decision_id,
                "workflow_version_id": str(getattr(execution, "workflow_version_id", "")),
                "completed_node_ids": completed_node_ids,
                "frontier_node_ids": frontier_node_ids,
                "selected_predecessors": selected_predecessors,
            },
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_trace_id(self, resume_execution: WorkflowExecution) -> str | None:
        result = await self.db.execute(
            select(WorkflowTraceEvent.trace_id)
            .where(
                WorkflowTraceEvent.execution_id == resume_execution.id,
                WorkflowTraceEvent.tenant_id == resume_execution.tenant_id,
                WorkflowTraceEvent.workflow_version_id == resume_execution.workflow_version_id,
                WorkflowTraceEvent.event_type == self.EVENT_TYPE,
            )
            .order_by(WorkflowTraceEvent.created_at.asc(), WorkflowTraceEvent.id.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()