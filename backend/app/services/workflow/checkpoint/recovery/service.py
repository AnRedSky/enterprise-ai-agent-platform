"""Workflow Checkpoint 恢复候选评估模块。

职责：只读判断已有 Checkpoint 是否满足未来 Durable Resume 的前置条件，并生成稳定的恢复候选标识。
边界：不修改 Execution/Node 状态、不抢占 Worker lease、不启动 Runtime、不提交数据库事务。
关键约束：恢复必须基于失败 Execution、无活动 Worker ownership、已完成 Node Checkpoint，并固定原 Execution 的 Workflow Version。
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint


@dataclass(frozen=True)
class WorkflowExecutionResumeAssessment:
    """Workflow Execution 的只读恢复候选评估结果。"""

    eligible: bool
    reason_code: str
    execution_id: UUID
    workflow_version_id: UUID
    checkpoint_id: UUID | None = None
    checkpoint_sequence: int | None = None
    node_id: str | None = None
    state_data: dict | None = None
    input_data: dict | None = None
    output_data: dict | None = None
    resume_idempotency_key: str | None = None


class WorkflowExecutionCheckpointRecoveryService:
    """负责定义 Durable Resume 的只读前置条件，不执行实际恢复。"""

    @staticmethod
    def assess(
        *,
        execution_id: UUID,
        workflow_version_id: UUID,
        execution_status: str,
        worker_owner: str | None,
        checkpoint: WorkflowExecutionCheckpoint | None,
    ) -> WorkflowExecutionResumeAssessment:
        """评估 Checkpoint 是否满足未来 Resume 的最小安全边界。

        Args:
            execution_id: 待评估的 Workflow Execution ID。
            workflow_version_id: 原 Execution 固定使用的 Workflow Version ID。
            execution_status: 当前持久化 Execution 状态。
            worker_owner: 当前持久化 Worker owner；存在 owner 时禁止生成可恢复候选。
            checkpoint: Execution 最新 Checkpoint；不存在时表示没有可恢复快照。

        Returns:
            只读评估结果。eligible 为 True 时表示具备未来 Resume 的基础条件，
            但本方法不会创建新 Execution、写入幂等键或获取 Worker ownership。

        Raises:
            ValueError: execution_id 或 workflow_version_id 不符合 UUID 类型要求时不会出现，
                调用方应直接传入 UUID；本方法不吞掉数据模型错误。

        重要边界：
            1. 当前只允许从 failed Execution 产生 Resume 候选；running Execution 必须先经过
               独立的 Worker lease recovery 边界，不能直接使用 Checkpoint 复活 Runtime。
            2. Worker owner 非空表示 ownership 仍有事实存在，即使调用者准备恢复也不得绕过 fencing。
            3. Checkpoint 必须来自 node.completed，且快照产生时 Execution 应处于 running 状态。
            4. Workflow Version 固定来自原 Execution；未来恢复不得隐式漂移到新的 published version。
            5. 幂等键由 `execution_id + checkpoint_sequence` 确定性生成，后续真正 Resume 时必须持久化并作为唯一约束的一部分。
        """
        if execution_status != "failed":
            return WorkflowExecutionResumeAssessment(
                eligible=False,
                reason_code="execution_not_failed",
                execution_id=execution_id,
                workflow_version_id=workflow_version_id,
            )

        if worker_owner is not None:
            return WorkflowExecutionResumeAssessment(
                eligible=False,
                reason_code="worker_ownership_active",
                execution_id=execution_id,
                workflow_version_id=workflow_version_id,
            )

        if checkpoint is None:
            return WorkflowExecutionResumeAssessment(
                eligible=False,
                reason_code="checkpoint_missing",
                execution_id=execution_id,
                workflow_version_id=workflow_version_id,
            )

        if checkpoint.checkpoint_reason != "node.completed":
            return WorkflowExecutionResumeAssessment(
                eligible=False,
                reason_code="checkpoint_not_resumable",
                execution_id=execution_id,
                workflow_version_id=workflow_version_id,
                checkpoint_id=checkpoint.id,
                checkpoint_sequence=checkpoint.sequence,
                node_id=checkpoint.node_id,
            )

        if checkpoint.execution_status != "running" or checkpoint.node_status != "completed" or checkpoint.node_id is None:
            return WorkflowExecutionResumeAssessment(
                eligible=False,
                reason_code="checkpoint_boundary_invalid",
                execution_id=execution_id,
                workflow_version_id=workflow_version_id,
                checkpoint_id=checkpoint.id,
                checkpoint_sequence=checkpoint.sequence,
                node_id=checkpoint.node_id,
            )

        return WorkflowExecutionResumeAssessment(
            eligible=True,
            reason_code="eligible",
            execution_id=execution_id,
            workflow_version_id=workflow_version_id,
            checkpoint_id=checkpoint.id,
            checkpoint_sequence=checkpoint.sequence,
            node_id=checkpoint.node_id,
            state_data=dict(checkpoint.state_data or {}),
            input_data=dict(checkpoint.input_data or {}) if checkpoint.input_data is not None else None,
            output_data=dict(checkpoint.output_data or {}) if checkpoint.output_data is not None else None,
            resume_idempotency_key=f"resume:{execution_id}:checkpoint:{checkpoint.sequence}",
        )
