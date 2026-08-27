"""Durable Resume creation outcome contract。

职责：在 Resume Domain 边界内把“创建 Resume”与“幂等命中”显式区分，并约束恢复候选使用确定性的幂等键。
边界：不复制 Resume 创建持久化逻辑；实际创建仍委托 WorkflowExecutionService。
并发语义：先锁定 Source Execution，再检查确定性 Resume 幂等键。所有正式 Resume 路径都会锁定同一 Source 行，因此同一 Source 的并发恢复调用在 Domain 内串行化；数据库唯一约束仍是最终安全兜底。
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowExecution
from app.services.workflow.checkpoint.recovery.service import WorkflowExecutionCheckpointRecoveryService
from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


@dataclass(frozen=True)
class WorkflowExecutionResumeOutcome:
    """一次 Resume Contract 调用的可观测结果。"""

    execution: WorkflowExecution
    outcome: str
    idempotency_key: str


class WorkflowExecutionResumeContractService:
    """为 Recovery Domain 提供 created / idempotency_hit 的稳定 Resume Contract。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.checkpoint = WorkflowExecutionCheckpointService(db)
        self.checkpoint_recovery = WorkflowExecutionCheckpointRecoveryService()

    async def resume_with_outcome(
        self,
        execution: WorkflowExecution,
        actor_id: UUID,
    ) -> WorkflowExecutionResumeOutcome:
        """在 Source Execution 锁内判断并执行一次确定性 Resume。

        Args:
            execution: 当前需要恢复的源 Workflow Execution。
            actor_id: 创建 Resume 时记录的操作者身份。

        Returns:
            明确区分 `created` 与 `idempotency_hit` 的 Resume 结果。

        Raises:
            ValueError: 恢复候选缺少确定性幂等键，或候选键与本地确定性规则不一致，
                或已有 Resume 的 lineage 与当前恢复请求不一致。

        事务边界：Source Execution 锁定与候选判断发生在调用方数据库事务内；实际 Resume 创建
        仍委托既有 WorkflowExecutionService，不在本 Contract 中复制持久化逻辑。
        """
        from app.services.workflow.execution import WorkflowExecutionService

        execution_service = WorkflowExecutionService(self.db)
        locked_execution = await execution_service._lock_execution(execution)
        checkpoint = await self.checkpoint.latest(
            locked_execution.id,
            tenant_id=locked_execution.tenant_id,
        )
        assessment = self.checkpoint_recovery.assess(
            execution_id=locked_execution.id,
            workflow_version_id=locked_execution.workflow_version_id,
            execution_status=locked_execution.status,
            worker_owner=locked_execution.worker_owner,
            checkpoint=checkpoint,
        )
        if assessment.resume_idempotency_key is None or assessment.checkpoint_sequence is None:
            raise ValueError("Resume Candidate 缺少确定性幂等键")

        expected_idempotency_key = (
            f"resume:{locked_execution.id}:checkpoint:{assessment.checkpoint_sequence}"
        )
        if assessment.resume_idempotency_key != expected_idempotency_key:
            raise ValueError("Resume Candidate 幂等键与 Source Execution / Checkpoint 不一致")

        existing = (await self.db.execute(select(WorkflowExecution).where(
            WorkflowExecution.tenant_id == locked_execution.tenant_id,
            WorkflowExecution.idempotency_key == assessment.resume_idempotency_key,
        ))).scalar_one_or_none()
        if existing is not None:
            if (
                existing.tenant_id != locked_execution.tenant_id
                or existing.workflow_id != locked_execution.workflow_id
                or existing.workflow_version_id != locked_execution.workflow_version_id
                or existing.resume_of_execution_id != locked_execution.id
                or existing.resume_checkpoint_sequence != assessment.checkpoint_sequence
            ):
                raise ValueError("Resume 幂等键已绑定不一致的 Execution lineage")
            return WorkflowExecutionResumeOutcome(
                execution=existing,
                outcome="idempotency_hit",
                idempotency_key=assessment.resume_idempotency_key,
            )

        resume_execution = await execution_service.resume_from_latest_checkpoint(
            locked_execution,
            actor_id,
        )
        return WorkflowExecutionResumeOutcome(
            execution=resume_execution,
            outcome="created",
            idempotency_key=assessment.resume_idempotency_key,
        )
