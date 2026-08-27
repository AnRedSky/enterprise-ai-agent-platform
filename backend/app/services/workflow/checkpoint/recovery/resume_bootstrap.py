"""Durable Resume Frontier Bootstrap 领域服务。

职责：把 Source Execution 的已完成 Node Durable Facts 复制到新的 Resume Execution，并计算首个 Resume Frontier。
边界：不启动 Runtime、不执行 Node；只在调用方事务中完成 Resume lineage 的 durable bootstrap 与 Frontier 入队。
关键依赖：WorkflowDagResumePlanner、WorkflowFrontierIdentity、WorkflowFrontier Repository、WorkflowNodeExecution。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowVersion
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution
from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner
from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_repository import enqueue_frontier


class WorkflowExecutionResumeBootstrapService:
    """在 Resume Execution 创建后建立 completed Node lineage 与首个 Durable Frontier。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def bootstrap(
        self,
        *,
        source_execution: WorkflowExecution,
        resume_execution: WorkflowExecution,
        actor_id,
    ) -> tuple[str, ...]:
        """复制 Source 的 completed Node facts，并为 Resume Execution 入队首个 frontier。

        Args:
            source_execution: 失败且已通过 Resume Contract 校验的源 Execution。
            resume_execution: 尚未启动 Runtime 的 pending Resume Execution。
            actor_id: Resume 创建操作者；用于复制 NodeExecution 的审计归属字段。

        Returns:
            tuple[str, ...]: 首个 Resume Frontier 的有序 Node IDs。

        Raises:
            ValueError: Source/Resume lineage、Workflow Version 或 completed Node facts 不一致。

        事务边界：本方法不 commit；调用方必须将 Node lineage 与 Frontier enqueue 与 Resume 创建放入同一事务。
        """
        if resume_execution.resume_of_execution_id != source_execution.id:
            raise ValueError("Resume Execution lineage 与 Source Execution 不一致")
        if resume_execution.workflow_version_id != source_execution.workflow_version_id:
            raise ValueError("Resume Execution 必须固定 Source Workflow Version")
        if resume_execution.status != "pending":
            raise ValueError("只有 pending Resume Execution 才能进行 Bootstrap")

        version = (
            await self.db.execute(
                select(WorkflowVersion).where(WorkflowVersion.id == source_execution.workflow_version_id)
            )
        ).scalar_one_or_none()
        if version is None:
            raise ValueError("Resume Source Workflow Version 不存在")
        nodes = WorkflowDagResumePlanner.plan if version.definition.get("edges") else None

        source_nodes_result = await self.db.execute(
            select(WorkflowNodeExecution)
            .where(
                WorkflowNodeExecution.execution_id == source_execution.id,
                WorkflowNodeExecution.status == "completed",
            )
            .order_by(WorkflowNodeExecution.created_at, WorkflowNodeExecution.node_id)
        )
        source_nodes = tuple(source_nodes_result.scalars().all())
        completed_ids = {node.node_id for node in source_nodes}
        state_data_by_node = {node.node_id: dict(node.output_data or {}) for node in source_nodes}

        for node in source_nodes:
            existing = (
                await self.db.execute(
                    select(WorkflowNodeExecution).where(
                        WorkflowNodeExecution.execution_id == resume_execution.id,
                        WorkflowNodeExecution.node_id == node.node_id,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                if existing.status != "completed" or existing.output_data != node.output_data:
                    raise ValueError(f"Resume Node lineage 与 Source Durable Fact 不一致: {node.node_id}")
                continue
            self.db.add(
                WorkflowNodeExecution(
                    execution_id=resume_execution.id,
                    node_id=node.node_id,
                    status="completed",
                    attempt=node.attempt,
                    input_data=dict(node.input_data or {}) if node.input_data is not None else None,
                    output_data=dict(node.output_data or {}) if node.output_data is not None else None,
                    error_code=None,
                    error_message=None,
                    started_at=node.started_at,
                    ended_at=node.ended_at,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
        await self.db.flush()

        if nodes is not None:
            plan = WorkflowDagResumePlanner.plan(
                definition=version.definition,
                completed_node_ids=completed_ids,
                state_data_by_node=state_data_by_node,
            )
            next_ids = plan.frontier_node_ids
            fingerprint = plan.decision_fingerprint
        else:
            ordered_ids = tuple(node["id"] for node in WorkflowDagResumePlanner._ordered_nodes(version.definition)) if hasattr(WorkflowDagResumePlanner, "_ordered_nodes") else tuple(node["id"] for node in version.definition.get("nodes", []))
            next_ids = tuple(node_id for node_id in ordered_ids if node_id not in completed_ids)[:1]
            fingerprint = f"resume:{source_execution.id}:{resume_execution.resume_checkpoint_sequence or 0}"

        if not next_ids:
            raise ValueError("Resume Bootstrap 没有可调度 Frontier；Source Checkpoint 与 Node facts 不一致")

        identity = WorkflowFrontierIdentity(
            execution_id=resume_execution.id,
            workflow_version_id=resume_execution.workflow_version_id,
            decision_fingerprint=fingerprint,
            node_ids=tuple(next_ids),
        )
        await enqueue_frontier(
            self.db,
            tenant_id=resume_execution.tenant_id,
            identity=identity,
            node_ids=identity.node_ids,
            now=datetime.now(UTC).replace(tzinfo=None),
        )
        return tuple(next_ids)
