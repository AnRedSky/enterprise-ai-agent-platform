"""Durable Recovery trace lineage link。

职责：把 Automatic Recovery 创建的 trace_id 持久化关联到 Resume Execution，
并验证 Source、Resume、Checkpoint 与已有 Trace 之间的同一条 lineage。
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
        """初始化 Recovery trace lineage 服务。

        Args:
            db: 当前请求或 Worker 生命周期内的异步数据库会话。
        """
        self.db = db

    async def _assert_resume_checkpoint_lineage(
        self,
        source_execution: WorkflowExecution,
        resume_execution: WorkflowExecution,
    ) -> int:
        """验证 Resume Execution 指向 Source 的同一 durable checkpoint 边界。

        Args:
            source_execution: Recovery 前的源 Execution。
            resume_execution: Recovery 创建的 Resume Execution。

        Returns:
            Source Execution 中真实存在的 checkpoint sequence。

        Raises:
            ValueError: Source/Resume 边界或 checkpoint 不一致。
        """
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
            raise ValueError(
                "Recovery trace lineage 的 resume_checkpoint_sequence 不存在于 Source Execution"
            )
        return checkpoint

    @staticmethod
    def _assert_existing_lineage_event(
        event: WorkflowTraceEvent,
        source_execution: WorkflowExecution,
        resume_execution: WorkflowExecution,
        checkpoint_sequence: int,
    ) -> None:
        """校验已存在的 lineage event，防止幂等命中掩盖错误关联。

        Args:
            event: 已持久化的 Recovery lineage event。
            source_execution: Recovery 前的源 Execution。
            resume_execution: Recovery 创建的 Resume Execution。
            checkpoint_sequence: 已验证的 Source checkpoint sequence。

        Raises:
            ValueError: 已有 event 与当前 Source/Resume lineage 不一致。
        """
        data = event.data if isinstance(event.data, dict) else {}
        expected = {
            "source_execution_id": str(source_execution.id),
            "resume_execution_id": str(resume_execution.id),
            "resume_checkpoint_sequence": checkpoint_sequence,
        }
        for key, value in expected.items():
            if data.get(key) != value:
                raise ValueError(f"Recovery trace lineage 已存在但 {key} 不一致")

    async def link(
        self,
        source_execution: WorkflowExecution,
        resume_execution: WorkflowExecution,
        trace_id: str,
        actor_id: UUID | None,
    ) -> WorkflowTraceEvent:
        """为 Resume Execution 建立可持久化的 Recovery trace 关联。

        Args:
            source_execution: Recovery 前的源 Execution。
            resume_execution: Recovery 创建的 Resume Execution。
            trace_id: Recovery 生命周期复用的 trace 标识。
            actor_id: 发起 Recovery 的操作者，可为空。

        Returns:
            新建或已存在且 lineage 完整一致的 Trace Event。

        Raises:
            ValueError: Source/Resume/Checkpoint 边界或已有 lineage 不一致。
        """
        checkpoint_sequence = await self._assert_resume_checkpoint_lineage(
            source_execution, resume_execution
        )
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
            self._assert_existing_lineage_event(
                existing, source_execution, resume_execution, checkpoint_sequence
            )
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
        """校验同一 Recovery trace 下完整 DAG Decision 是否可确定性重建。

        Args:
            execution: 当前 Recovery Execution，用于限定 tenant 与 workflow version。
            trace_id: 当前 Recovery 生命周期的 trace 标识。
            completed_node_ids: 当前 durable snapshot 已完成的节点。
            decision_fingerprint: Planner 生成的 Decision 身份指纹。
            frontier_node_ids: 当前 Planner 计算出的 frontier。
            selected_predecessors: 当前 Planner 计算出的 predecessor 选择。

        Raises:
            ValueError: 历史 Decision 与当前 Decision 不一致。
        """
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
                raise ValueError(
                    "DAG Recovery Decision fingerprint 不一致：同一 durable completed facts 产生了不同 Decision"
                )
            if frontier_node_ids is not None and data.get("frontier_node_ids") != frontier_node_ids:
                raise ValueError(
                    "DAG Recovery Decision frontier 不一致：同一 durable completed facts 产生了不同 frontier"
                )
            if selected_predecessors is not None and data.get("selected_predecessors") != selected_predecessors:
                raise ValueError(
                    "DAG Recovery Decision predecessor 不一致：同一 durable completed facts 产生了不同 predecessor selection"
                )

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
        """幂等持久化 DAG frontier decision，并保持 Decision Trace 不重复增长。

        Args:
            execution: 当前 Workflow Execution。
            trace_id: 当前 trace 标识；为空时不持久化。
            actor_id: 发起动作的操作者，可为空。
            decision_id: Planner 生成的 Decision identity。
            completed_node_ids: 当前已完成节点集合。
            frontier_node_ids: Planner 选出的 frontier。
            selected_predecessors: Planner 选出的 predecessor facts。

        Returns:
            新建或命中的 Decision Trace Event；无 trace_id 时返回 None。
        """
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
        """从持久化 Recovery lineage 恢复 Resume Execution 对应的 trace_id。

        Args:
            resume_execution: 需要恢复 trace 的 Resume Execution。

        Returns:
            与当前 tenant、workflow version、Resume Execution 对应的 trace_id。
        """
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
