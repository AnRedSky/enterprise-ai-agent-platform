"""Workflow Execution Checkpoint 领域服务。

负责 Workflow Execution Checkpoint 的持久化边界，并保证同一 Execution 的序号分配在并发 Worker 下保持串行一致。
本模块不负责恢复调度、状态机推进或 Worker ownership 校验。
关键依赖：Workflow Execution / Node Execution ORM 与 SQLAlchemy AsyncSession。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution


class WorkflowExecutionCheckpointService:
    """负责 Workflow Execution Checkpoint 的持久化边界。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _validate(sequence: int, checkpoint_reason: str) -> None:
        """校验 Checkpoint 序号与原因，避免写入不可恢复的非法快照。"""
        if sequence < 0:
            raise ValueError("Checkpoint sequence 必须大于等于 0")
        if not checkpoint_reason.strip():
            raise ValueError("Checkpoint reason 不能为空")

    @staticmethod
    def assert_node_fact_complete(*, checkpoint, node_execution) -> None:
        """验证带 Node 的 Checkpoint 与对应 NodeExecution 属于同一 Durable Fact。

        Execution-level checkpoint（node_id=None）不绑定 NodeExecution；带 node_id 的 checkpoint
        必须能找到同一 Node，且 status、attempt、output_data 完全一致。这样 Recovery 不会把不同
        时间边界的 NodeExecution 与 Checkpoint 拼成一个 snapshot。
        """
        if checkpoint.node_id is None:
            return
        if node_execution is None:
            raise ValueError(f"Checkpoint 对应的 NodeExecution 不存在: {checkpoint.node_id}")
        if node_execution.node_id != checkpoint.node_id:
            raise ValueError(f"Checkpoint node_id 与 NodeExecution 不一致: {checkpoint.node_id}")
        if checkpoint.node_status is not None and node_execution.status != checkpoint.node_status:
            raise ValueError(f"Checkpoint node status 与 NodeExecution 不一致: {checkpoint.node_id}")
        if checkpoint.node_attempt is not None and node_execution.attempt != checkpoint.node_attempt:
            raise ValueError(f"Checkpoint attempt 与 NodeExecution 不一致: {checkpoint.node_id}")
        if checkpoint.output_data != node_execution.output_data:
            raise ValueError(f"Checkpoint output_data 与 NodeExecution 不一致: {checkpoint.node_id}")

    @staticmethod
    def _validate_worker_fencing(
        *,
        expected_worker_owner: str | None,
        expected_worker_attempt: int | None,
        execution: WorkflowExecution,
    ) -> None:
        """校验 Checkpoint 写入时的 Execution owner/generation，阻断 stale Worker。

        Checkpoint 是不可变 Durable Fact；如果调用方来自 Worker，必须在目标 Execution 行锁定后
        再确认 owner 与 generation 仍然一致。这样即使旧 Worker 持有已经过期的上下文，也不能在
        Frontier fencing 之外单独追加 Checkpoint。
        """
        if expected_worker_owner is None and expected_worker_attempt is None:
            return
        if expected_worker_owner is None or expected_worker_attempt is None:
            raise HTTPException(409, "Checkpoint Worker fencing 参数不完整")
        locked_attempt = int(execution.worker_attempt or 0)
        if execution.worker_owner != expected_worker_owner or locked_attempt != expected_worker_attempt:
            raise HTTPException(409, "Checkpoint Worker ownership 或 fencing generation 已失效")

    def _build(self, *, execution_id: UUID, sequence: int, execution_status: str, state_data: dict,
               checkpoint_reason: str, node_id: str | None = None, node_attempt: int | None = None,
               node_status: str | None = None, input_data: dict | None = None, output_data: dict | None = None,
               worker_owner: str | None = None, error_code: str | None = None,
               error_message: str | None = None) -> WorkflowExecutionCheckpoint:
        self._validate(sequence, checkpoint_reason)
        return WorkflowExecutionCheckpoint(
            execution_id=execution_id, sequence=sequence, node_id=node_id, node_attempt=node_attempt,
            execution_status=execution_status, node_status=node_status, state_data=state_data,
            input_data=input_data, output_data=output_data, checkpoint_reason=checkpoint_reason,
            worker_owner=worker_owner, error_code=error_code, error_message=error_message,
        )

    async def append(self, *, execution_id: UUID, sequence: int, execution_status: str, state_data: dict,
                     checkpoint_reason: str, node_id: str | None = None, node_attempt: int | None = None,
                     node_status: str | None = None, input_data: dict | None = None, output_data: dict | None = None,
                     worker_owner: str | None = None, error_code: str | None = None,
                     error_message: str | None = None) -> WorkflowExecutionCheckpoint:
        checkpoint = self._build(execution_id=execution_id, sequence=sequence, execution_status=execution_status,
                                 state_data=state_data, checkpoint_reason=checkpoint_reason, node_id=node_id,
                                 node_attempt=node_attempt, node_status=node_status, input_data=input_data,
                                 output_data=output_data, worker_owner=worker_owner, error_code=error_code,
                                 error_message=error_message)
        self.db.add(checkpoint)
        await self.db.commit()
        await self.db.refresh(checkpoint)
        return checkpoint

    async def append_next_in_transaction(self, *, execution_id: UUID, execution_status: str, state_data: dict,
                                        checkpoint_reason: str, node_id: str | None = None,
                                        node_attempt: int | None = None, node_status: str | None = None,
                                        input_data: dict | None = None, output_data: dict | None = None,
                                        worker_owner: str | None = None, error_code: str | None = None,
                                        error_message: str | None = None, tenant_id: UUID | None = None,
                                        expected_worker_owner: str | None = None,
                                        expected_worker_attempt: int | None = None) -> WorkflowExecutionCheckpoint:
        """在调用方事务中写入下一个 Checkpoint，并校验 tenant 与 Worker fencing generation。

        Args:
            execution_id: 目标 Workflow Execution。
            execution_status: Checkpoint 对应的 Execution 状态。
            state_data: Checkpoint 的持久化状态快照。
            checkpoint_reason: 生成 Checkpoint 的业务原因。
            node_id: Node-level Checkpoint 对应的节点标识。
            node_attempt: Node Execution attempt。
            node_status: Node Execution 状态。
            input_data: Node 输入快照。
            output_data: Node 输出快照。
            worker_owner: 写入事实中记录的 Worker owner。
            error_code: 可选错误码。
            error_message: 可选错误信息。
            tenant_id: 可选 tenant scope。
            expected_worker_owner: Worker 写入上下文中的 owner；提供后强制执行 fencing。
            expected_worker_attempt: Worker 写入上下文中的 generation；提供后强制执行 fencing。

        Returns:
            新创建且尚未提交的 WorkflowExecutionCheckpoint。

        Raises:
            HTTPException: Execution 不存在、tenant 不匹配或 Worker fencing 已失效。
        """
        self._validate(0, checkpoint_reason)
        execution_query = select(WorkflowExecution).where(WorkflowExecution.id == execution_id).with_for_update()
        if tenant_id is not None:
            execution_query = execution_query.where(WorkflowExecution.tenant_id == tenant_id)
        execution_result = await self.db.execute(execution_query)
        execution = execution_result.scalar_one_or_none()
        if execution is None:
            raise HTTPException(409, f"Checkpoint 对应的 Workflow Execution 不存在或不属于当前 tenant: {execution_id}")
        self._validate_worker_fencing(
            expected_worker_owner=expected_worker_owner,
            expected_worker_attempt=expected_worker_attempt,
            execution=execution,
        )
        latest_sequence = await self.db.execute(
            select(func.max(WorkflowExecutionCheckpoint.sequence)).where(
                WorkflowExecutionCheckpoint.execution_id == execution_id
            )
        )
        current_sequence = latest_sequence.scalar_one()
        sequence = 0 if current_sequence is None else current_sequence + 1
        checkpoint = self._build(execution_id=execution_id, sequence=sequence, execution_status=execution_status,
                                 state_data=state_data, checkpoint_reason=checkpoint_reason, node_id=node_id,
                                 node_attempt=node_attempt, node_status=node_status, input_data=input_data,
                                 output_data=output_data, worker_owner=worker_owner, error_code=error_code,
                                 error_message=error_message)
        self.db.add(checkpoint)
        await self.db.flush()
        return checkpoint

    async def latest(self, execution_id: UUID, *, tenant_id: UUID | None = None) -> WorkflowExecutionCheckpoint | None:
        query = (select(WorkflowExecutionCheckpoint)
                 .join(WorkflowExecution, WorkflowExecution.id == WorkflowExecutionCheckpoint.execution_id)
                 .where(WorkflowExecutionCheckpoint.execution_id == execution_id))
        if tenant_id is not None:
            query = query.where(WorkflowExecution.tenant_id == tenant_id)
        result = await self.db.execute(query.order_by(desc(WorkflowExecutionCheckpoint.sequence)).limit(1))
        return result.scalar_one_or_none()

    async def latest_recovery_fact(self, execution_id: UUID, *, tenant_id: UUID | None = None):
        """读取最新 checkpoint，并验证其 Node fact 未与 Durable NodeExecution 脱节。"""
        checkpoint = await self.latest(execution_id, tenant_id=tenant_id)
        if checkpoint is None:
            return None
        node_execution = None
        if checkpoint.node_id is not None:
            node_query = select(WorkflowNodeExecution).join(
                WorkflowExecution, WorkflowExecution.id == WorkflowNodeExecution.execution_id
            ).where(
                WorkflowNodeExecution.execution_id == execution_id,
                WorkflowNodeExecution.node_id == checkpoint.node_id,
            )
            if tenant_id is not None:
                node_query = node_query.where(WorkflowExecution.tenant_id == tenant_id)
            result = await self.db.execute(node_query)
            node_execution = result.scalar_one_or_none()
        self.assert_node_fact_complete(checkpoint=checkpoint, node_execution=node_execution)
        return checkpoint
