"""Workflow Durable Resume 自动恢复领域服务。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from time import monotonic
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowExecution
from app.services.workflow.checkpoint.recovery.observability import (
    RECOVERY_ATTEMPT,
    WorkflowRecoveryEvent,
    WorkflowRecoveryEventLogger,
    WorkflowRecoveryTelemetry,
)
from app.services.workflow.checkpoint.recovery.policy import (
    WorkflowExecutionRecoveryDecision,
    WorkflowExecutionRecoveryPolicy,
    WorkflowExecutionRecoveryPolicyEvaluator,
)
from app.services.workflow.checkpoint.recovery.resume_contract import WorkflowExecutionResumeContractService
from app.services.workflow.checkpoint.recovery.service import WorkflowExecutionCheckpointRecoveryService
from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService
from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


@dataclass(frozen=True)
class WorkflowExecutionAutomaticRecoveryResult:
    """自动恢复评估及执行结果。"""

    decision: WorkflowExecutionRecoveryDecision
    resume_execution_id: UUID | None = None
    outcome: str = "rejected"


class WorkflowExecutionAutomaticRecoveryService:
    """执行单个 failed Execution 的自动恢复评估与 Resume 创建。"""

    def __init__(self, db: AsyncSession, policy: WorkflowExecutionRecoveryPolicy | None = None, event_logger: WorkflowRecoveryEventLogger | None = None, telemetry: WorkflowRecoveryTelemetry | None = None):
        self.db = db
        self.policy = WorkflowExecutionRecoveryPolicyEvaluator(policy)
        self.checkpoint_recovery = WorkflowExecutionCheckpointRecoveryService()
        self.checkpoint = WorkflowExecutionCheckpointService(db)
        self.resume_contract = WorkflowExecutionResumeContractService(db)
        self.trace_link = WorkflowRecoveryTraceLinkService(db)
        self.event_logger = event_logger or WorkflowRecoveryEventLogger(logging.getLogger(__name__))
        self.telemetry = telemetry or WorkflowRecoveryTelemetry(event_logger=self.event_logger)

    async def _count_resume_ancestors(self, execution: WorkflowExecution) -> int:
        count = 0
        current_id = execution.resume_of_execution_id
        visited: set[UUID] = set()
        while current_id is not None:
            if current_id in visited:
                break
            visited.add(current_id)
            result = await self.db.execute(select(WorkflowExecution.resume_of_execution_id).where(WorkflowExecution.id == current_id, WorkflowExecution.tenant_id == execution.tenant_id))
            parent_id = result.scalar_one_or_none()
            count += 1
            current_id = parent_id
        return count

    async def evaluate(self, execution: WorkflowExecution, *, now: datetime | None = None) -> WorkflowExecutionAutomaticRecoveryResult:
        """评估一个 failed Execution 是否满足自动 Resume 策略；不会创建 Resume。

        Args:
            execution: 待评估的 Workflow Execution。
            now: 策略评估使用的当前时间。

        Returns:
            WorkflowExecutionAutomaticRecoveryResult: 包含 eligibility、原因与历史恢复次数的评估结果。

        设计意图：active Worker 是恢复资格的硬拒绝条件，必须在读取 Checkpoint 前短路，避免无效的自动恢复扫描访问不完整的 Durable 状态。
        """
        if execution.status != "failed":
            decision = self.policy.evaluate(
                execution_status=execution.status,
                worker_owner=execution.worker_owner,
                checkpoint_eligible=False,
                resume_attempt_count=0,
                ended_at=execution.ended_at,
                now=now,
            )
            return WorkflowExecutionAutomaticRecoveryResult(decision=decision)
        if execution.worker_owner is not None:
            decision = self.policy.evaluate(
                execution_status=execution.status,
                worker_owner=execution.worker_owner,
                checkpoint_eligible=False,
                resume_attempt_count=0,
                ended_at=execution.ended_at,
                now=now,
            )
            return WorkflowExecutionAutomaticRecoveryResult(decision=decision)

        checkpoint = await self.checkpoint.latest_recovery_fact(
            execution.id,
            tenant_id=execution.tenant_id,
        )
        assessment = self.checkpoint_recovery.assess(execution_id=execution.id, workflow_version_id=execution.workflow_version_id, execution_status=execution.status, worker_owner=execution.worker_owner, checkpoint=checkpoint)
        attempts = await self._count_resume_ancestors(execution)
        decision = self.policy.evaluate(execution_status=execution.status, worker_owner=execution.worker_owner, checkpoint_eligible=assessment.eligible, resume_attempt_count=attempts, ended_at=execution.ended_at, now=now)
        return WorkflowExecutionAutomaticRecoveryResult(decision=decision)

    def _emit_attempt(self, execution: WorkflowExecution, result: WorkflowExecutionAutomaticRecoveryResult, *, trace_id: str | None = None, parent_trace_id: str | None = None, duration_ms: float | None = None) -> None:
        self.telemetry.emit(WorkflowRecoveryEvent(event_name=RECOVERY_ATTEMPT, execution_id=execution.id, resume_execution_id=result.resume_execution_id, outcome=result.outcome, reason_code=result.decision.reason_code, attempt_count=result.decision.attempt_count, max_attempts=result.decision.max_attempts, trace_id=trace_id, parent_trace_id=parent_trace_id, phase="automatic_recovery", duration_ms=duration_ms))

    async def recover(self, execution: WorkflowExecution, *, actor_id: UUID | None = None, now: datetime | None = None, parent_trace_id: str | None = None) -> WorkflowExecutionAutomaticRecoveryResult:
        started = monotonic()
        trace_id = self.telemetry.start_trace(execution_id=execution.id, phase="automatic_recovery", parent_trace_id=parent_trace_id)
        result = await self.evaluate(execution, now=now)
        if not result.decision.eligible:
            rejected = WorkflowExecutionAutomaticRecoveryResult(decision=result.decision, outcome="rejected")
            duration_ms = (monotonic() - started) * 1000
            self._emit_attempt(execution, rejected, trace_id=trace_id, parent_trace_id=parent_trace_id, duration_ms=duration_ms)
            self.telemetry.finish_trace(trace_id, execution_id=execution.id, outcome=rejected.outcome, reason_code=rejected.decision.reason_code, phase="automatic_recovery", parent_trace_id=parent_trace_id, duration_ms=duration_ms)
            return rejected
        resume_result = await self.resume_contract.resume_with_outcome(
            execution,
            actor_id or execution.created_by,
            commit=False,
        )
        recovered = WorkflowExecutionAutomaticRecoveryResult(decision=result.decision, resume_execution_id=resume_result.execution.id, outcome=resume_result.outcome)
        await self.trace_link.link(
            execution,
            resume_result.execution,
            trace_id,
            actor_id or execution.created_by,
            commit=False,
        )
        await self.db.commit()
        duration_ms = (monotonic() - started) * 1000
        self._emit_attempt(execution, recovered, trace_id=trace_id, parent_trace_id=parent_trace_id, duration_ms=duration_ms)
        self.telemetry.finish_trace(trace_id, execution_id=execution.id, resume_execution_id=recovered.resume_execution_id, outcome=recovered.outcome, reason_code=recovered.decision.reason_code, phase="automatic_recovery", parent_trace_id=parent_trace_id, duration_ms=duration_ms)
        return recovered
