"""Workflow Durable Resume 自动恢复领域服务。

职责：将恢复策略、Checkpoint 候选评估与现有 Resume Domain Contract 串成一次受控的自动恢复操作。
边界：不负责 Scheduler 轮询时间、不直接抢 Worker ownership、不直接启动 Runtime；真正创建 Resume Execution 委托 WorkflowExecutionService。
关键依赖：WorkflowExecution ORM、Checkpoint Recovery Service、Recovery Policy、WorkflowExecutionService。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowExecution
from app.services.workflow.checkpoint.recovery.policy import (
    WorkflowExecutionRecoveryDecision,
    WorkflowExecutionRecoveryPolicy,
    WorkflowExecutionRecoveryPolicyEvaluator,
)
from app.services.workflow.checkpoint.recovery.service import WorkflowExecutionCheckpointRecoveryService
from app.services.workflow.execution import WorkflowExecutionService


@dataclass(frozen=True)
class WorkflowExecutionAutomaticRecoveryResult:
    """自动恢复评估及执行结果。"""

    decision: WorkflowExecutionRecoveryDecision
    resume_execution_id: UUID | None = None


class WorkflowExecutionAutomaticRecoveryService:
    """执行单个 failed Execution 的自动恢复评估与 Resume 创建。"""

    def __init__(
        self,
        db: AsyncSession,
        policy: WorkflowExecutionRecoveryPolicy | None = None,
    ):
        self.db = db
        self.policy = WorkflowExecutionRecoveryPolicyEvaluator(policy)
        self.checkpoint_recovery = WorkflowExecutionCheckpointRecoveryService()

    async def _count_resume_ancestors(self, execution: WorkflowExecution) -> int:
        """沿 Resume lineage 统计该 Execution 之前已经发生的自动恢复链长度。

        Args:
            execution: 当前需要判断恢复次数的 Execution。

        Returns:
            当前 Execution 之前的 Resume lineage 深度；普通初始 Execution 为 0。

        事务边界：只读查询，不修改数据库；每一级都限定 tenant，避免跨租户 lineage 被错误计数。
        """
        count = 0
        current_id = execution.resume_of_execution_id
        visited: set[UUID] = set()
        while current_id is not None:
            if current_id in visited:
                break
            visited.add(current_id)
            result = await self.db.execute(
                select(WorkflowExecution.resume_of_execution_id).where(
                    WorkflowExecution.id == current_id,
                    WorkflowExecution.tenant_id == execution.tenant_id,
                )
            )
            parent_id = result.scalar_one_or_none()
            count += 1
            current_id = parent_id
        return count

    async def evaluate(
        self,
        execution: WorkflowExecution,
        *,
        now: datetime | None = None,
    ) -> WorkflowExecutionAutomaticRecoveryResult:
        """评估一个 failed Execution 是否满足自动 Resume 策略。

        Args:
            execution: 待恢复的 Workflow Execution。
            now: 可选当前时间，便于确定性测试；未传入时由策略使用 UTC 当前时间。

        Returns:
            只读自动恢复结果；不满足条件时 resume_execution_id 为 None。

        Raises:
            ValueError: lineage 数据非法时由底层策略或数据访问直接暴露。

        重要边界：只读评估不会创建 Resume Execution；调用方必须显式调用 recover() 才会产生副作用。
        """
        checkpoint = await self.checkpoint_recovery_service().latest(execution.id)
        assessment = self.checkpoint_recovery.assess(
            execution_id=execution.id,
            workflow_version_id=execution.workflow_version_id,
            execution_status=execution.status,
            worker_owner=execution.worker_owner,
            checkpoint=checkpoint,
        )
        attempts = await self._count_resume_ancestors(execution)
        decision = self.policy.evaluate(
            execution_status=execution.status,
            worker_owner=execution.worker_owner,
            checkpoint_eligible=assessment.eligible,
            resume_attempt_count=attempts,
            ended_at=execution.ended_at,
            now=now,
        )
        return WorkflowExecutionAutomaticRecoveryResult(decision=decision)

    def checkpoint_recovery_service(self):
        """创建使用当前数据库会话的 Checkpoint Service，保持恢复查询与调用方事务一致。"""
        from app.services.workflow.checkpoint import WorkflowExecutionCheckpointService
        return WorkflowExecutionCheckpointService(self.db)

    async def recover(
        self,
        execution: WorkflowExecution,
        *,
        actor_id: UUID | None = None,
        now: datetime | None = None,
    ) -> WorkflowExecutionAutomaticRecoveryResult:
        """执行一次受策略约束的自动 Resume。

        Args:
            execution: 待恢复的 failed Workflow Execution。
            actor_id: 自动恢复产生的审计身份；未提供时沿用 Execution 创建者。
            now: 可选当前时间，用于冷却窗口判断。

        Returns:
            若 eligible，返回新建或幂等命中的 Resume Execution ID；否则仅返回拒绝决策。

        事务边界：本方法自身不获取 Worker ownership。通过 WorkflowExecutionService 创建新的 pending
        Resume Execution，Source failed Execution 保持原状态，随后由标准 Worker claim 路径消费。
        """
        result = await self.evaluate(execution, now=now)
        if not result.decision.eligible:
            return result
        service = WorkflowExecutionService(self.db)
        resume_execution = await service.resume_from_latest_checkpoint(
            execution,
            actor_id or execution.created_by,
        )
        return WorkflowExecutionAutomaticRecoveryResult(
            decision=result.decision,
            resume_execution_id=resume_execution.id,
        )
