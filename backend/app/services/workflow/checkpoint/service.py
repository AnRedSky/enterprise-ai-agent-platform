"""Workflow Execution Checkpoint 领域服务。

负责 Workflow Execution Checkpoint 的持久化边界，并保证同一 Execution 的序号分配在并发 Worker 下保持串行一致。
本模块不负责恢复调度、状态机推进或 Worker ownership 校验。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_execution import WorkflowExecution


class WorkflowExecutionCheckpointService:
    """负责 Workflow Execution Checkpoint 的持久化边界。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _validate(sequence: int, checkpoint_reason: str) -> None:
        """校验 Checkpoint 序号与原因，避免写入不可恢复的非法快照。

        Args:
            sequence: Checkpoint 在当前 Execution 中的单调序号。
            checkpoint_reason: 记录本次快照产生原因的非空文本。
        """
        if sequence < 0:
            raise ValueError("Checkpoint sequence 必须大于等于 0")
        if not checkpoint_reason.strip():
            raise ValueError("Checkpoint reason 不能为空")

    def _build(
        self,
        *,
        execution_id: UUID,
        sequence: int,
        execution_status: str,
        state_data: dict,
        checkpoint_reason: str,
        node_id: str | None = None,
        node_attempt: int | None = None,
        node_status: str | None = None,
        input_data: dict | None = None,
        output_data: dict | None = None,
        worker_owner: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> WorkflowExecutionCheckpoint:
        self._validate(sequence, checkpoint_reason)
        return WorkflowExecutionCheckpoint(
            execution_id=execution_id,
            sequence=sequence,
            node_id=node_id,
            node_attempt=node_attempt,
            execution_status=execution_status,
            node_status=node_status,
            state_data=state_data,
            input_data=input_data,
            output_data=output_data,
            checkpoint_reason=checkpoint_reason,
            worker_owner=worker_owner,
            error_code=error_code,
            error_message=error_message,
        )

    async def append(
        self,
        *,
        execution_id: UUID,
        sequence: int,
        execution_status: str,
        state_data: dict,
        checkpoint_reason: str,
        node_id: str | None = None,
        node_attempt: int | None = None,
        node_status: str | None = None,
        input_data: dict | None = None,
        output_data: dict | None = None,
        worker_owner: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> WorkflowExecutionCheckpoint:
        """追加指定序号的 Checkpoint，并提交当前事务。

        Args:
            execution_id: 目标 Workflow Execution 标识。
            sequence: 调用方已经确定的 Checkpoint 序号。
            execution_status: 写入快照时的 Execution 状态。
            state_data: 用于恢复的持久化状态快照。
            checkpoint_reason: 本次快照产生原因。
            node_id: 触发快照的 Node 标识。
            node_attempt: Node 当前尝试次数。
            node_status: Node 写入快照时的状态。
            input_data: Node 输入快照。
            output_data: Node 输出快照。
            worker_owner: 当前 Worker ownership 标识。
            error_code: 失败时的稳定错误码。
            error_message: 失败时的错误描述。

        Returns:
            已持久化并刷新数据库字段的 Checkpoint 实例。
        """
        checkpoint = self._build(
            execution_id=execution_id,
            sequence=sequence,
            execution_status=execution_status,
            state_data=state_data,
            checkpoint_reason=checkpoint_reason,
            node_id=node_id,
            node_attempt=node_attempt,
            node_status=node_status,
            input_data=input_data,
            output_data=output_data,
            worker_owner=worker_owner,
            error_code=error_code,
            error_message=error_message,
        )
        self.db.add(checkpoint)
        await self.db.commit()
        await self.db.refresh(checkpoint)
        return checkpoint

    async def append_next_in_transaction(
        self,
        *,
        execution_id: UUID,
        execution_status: str,
        state_data: dict,
        checkpoint_reason: str,
        node_id: str | None = None,
        node_attempt: int | None = None,
        node_status: str | None = None,
        input_data: dict | None = None,
        output_data: dict | None = None,
        worker_owner: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> WorkflowExecutionCheckpoint:
        """在当前事务内分配下一个 Checkpoint 序号并追加快照。

        Args:
            execution_id: 目标 Workflow Execution 标识。
            execution_status: 写入快照时的 Execution 状态。
            state_data: 用于恢复的持久化状态快照。
            checkpoint_reason: 本次快照产生原因。
            node_id: 触发快照的 Node 标识。
            node_attempt: Node 当前尝试次数。
            node_status: Node 写入快照时的状态。
            input_data: Node 输入快照。
            output_data: Node 输出快照。
            worker_owner: 当前 Worker ownership 标识。
            error_code: 失败时的稳定错误码。
            error_message: 失败时的错误描述。

        Returns:
            已加入当前事务、尚未独立提交的 Checkpoint 实例。

        Raises:
            ValueError: Checkpoint 原因为空或序号规则非法时抛出。

        设计约束：同一 Execution 的序号必须在数据库事务内串行分配。先锁定 Execution 行，再读取最大序号，避免两个 Worker 同时计算出相同的 sequence 并触发唯一键冲突。
        """
        self._validate(0, checkpoint_reason)
        execution_result = await self.db.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .with_for_update()
        )
        execution = execution_result.scalar_one_or_none()
        if execution is None:
            raise ValueError(f"Checkpoint 对应的 Workflow Execution 不存在: {execution_id}")

        latest_sequence = await self.db.execute(
            select(func.max(WorkflowExecutionCheckpoint.sequence)).where(
                WorkflowExecutionCheckpoint.execution_id == execution_id
            )
        )
        current_sequence = latest_sequence.scalar_one()
        sequence = 0 if current_sequence is None else current_sequence + 1
        checkpoint = self._build(
            execution_id=execution_id,
            sequence=sequence,
            execution_status=execution_status,
            state_data=state_data,
            checkpoint_reason=checkpoint_reason,
            node_id=node_id,
            node_attempt=node_attempt,
            node_status=node_status,
            input_data=input_data,
            output_data=output_data,
            worker_owner=worker_owner,
            error_code=error_code,
            error_message=error_message,
        )
        self.db.add(checkpoint)
        await self.db.flush()
        return checkpoint

    async def latest(self, execution_id: UUID, *, tenant_id: UUID | None = None) -> WorkflowExecutionCheckpoint | None:
        """读取最新 Checkpoint；提供 tenant_id 时强制通过 Execution 关系限定租户。"""
        query = (
            select(WorkflowExecutionCheckpoint)
            .join(WorkflowExecution, WorkflowExecution.id == WorkflowExecutionCheckpoint.execution_id)
            .where(WorkflowExecutionCheckpoint.execution_id == execution_id)
        )
        if tenant_id is not None:
            query = query.where(WorkflowExecution.tenant_id == tenant_id)
        result = await self.db.execute(query.order_by(desc(WorkflowExecutionCheckpoint.sequence)).limit(1))
        return result.scalar_one_or_none()
