"""Workflow Durable Resume 自动恢复领域服务。

职责：将恢复策略、Checkpoint 候选评估与现有 Resume Domain Contract 串成一次受控的自动恢复操作。
边界：不负责 Scheduler 轮询时间、不直接抢 Worker ownership、不直接启动 Runtime；真正创建 Resume Execution 委托 WorkflowExecutionService。
关键依赖：WorkflowExecution ORM、Checkpoint Recovery Service、Recovery Policy、WorkflowExecutionService、Recovery Observability Event。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowExecution
from app.services.workflow.checkpoint.recovery.observability import (
    RECOVERY_ATTEMPT,
    WorkflowRecoveryEvent,
    WorkflowRecoveryEventLogger,
)
from app.services.workflow.checkpoint.recovery.policy import (
    WorkflowExecutionRecoveryDecision,
    WorkflowExecutionRecoveryPolicy,
    WorkflowExecutionRecoveryPolicyEvaluator,
)
from app.services.workflow.checkpoint.recovery.service import WorkflowExecutionCheckpointRecoveryService
from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


@dataclass(frozen=True)
class WorkflowExecutionAutomaticRecoveryResult:
    """自动恢复评估及执行结果。"""

    decision: WorkflowExecutionRecoveryDecision
    resume_execution_id: UUID | None = None
    outcome: str = "rejected"


class WorkflowExecutionAutomaticRecoveryService:
    """执行单个 failed Execution 的自动恢复评估与 Resume 创建。"""

    def __init__(
        self,
        db: AsyncSession,
        policy: WorkflowExecutionRecoveryPolicy | None = None,
        event_logger: WorkflowRecoveryEventLogger | None = None,
    ):
        self.db = db
        self.policy = WorkflowExecutionRecoveryPolicyEvaluator(policy)
        self.checkpoint_recovery = WorkflowExecutionCheckpointRecoveryService()
        self.checkpoint = WorkflowExecutionCheckpointService(db)
        self.event_logger = event_logger or WorkflowRecoveryEventLogger(logging.getLogger(__name__))

    async def _count_resume_ancestors(self, execution: WorkflowExecution) -> int:
        """沿 Resume lineage 统计该 Execution 之前已经发生的恢复链长度。"""
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
        """评估一个 failed Execution 是否满足自动 Resume 策略；不会创建 Resume。"""
        checkpoint = await self.checkpoint.latest(execution.id)
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

    def _emit_attempt(
        self,
        execution: WorkflowExecution,
        result: WorkflowExecutionAutomaticRecoveryResult,
    ) -> None:
        """输出一次 Recovery attempt 事件；事件不包含业务 payload。"""
        self.event_logger.emit(
            WorkflowRecoveryEvent(
                event_name=RECOVERY_ATTEMPT,
                execution_id=execution.id,
                resume_execution_id=result.resume_execution_id,
                reason_code=result.decision.reason_code,
                attempt_count=result.decision.attempt_count,
                max_attempts=result.decision.max_attempts,
            )
        )

    async def recover(
        self,
        execution: WorkflowExecution,
        *,
        actor_id: UUID | None = None,
        now: datetime | None = None,
    ) -> WorkflowExecutionAutomaticRecoveryResult:
        """执行一次受策略约束的自动 Resume，并返回可区分的恢复结果。"""
        result = await self.evaluate(execution, now=now)
        if not result.decision.eligible:
            rejected = WorkflowExecutionAutomaticRecoveryResult(
                decision=result.decision,
                outcome="rejected",
            )
            self._emit_attempt(execution, rejected)
            return rejected

        from app.services.workflow.execution import WorkflowExecutionService

        resume_execution = await WorkflowExecutionService(self.db).resume_from_latest_checkpoint(
            execution,
            actor_id or execution.created_by,
        )
        recovered = WorkflowExecutionAutomaticRecoveryResult(
            decision=result.decision,
            resume_execution_id=resume_execution.id,
            outcome="recovered",
        )
        self._emit_attempt(execution, recovered)
        return recovered
