"""Workflow Execution Checkpoint 领域服务。

负责 Workflow Execution Checkpoint 的持久化边界，并保证同一 Execution 的序号分配在并发 Worker 下保持串行一致。
本模块不负责恢复调度、状态机推进或 Worker ownership 校验。
关键依赖：SQLAlchemy AsyncSession、Workflow Execution / Node Execution ORM。
"""

from __future__ import annotations

from datetime import UTC, datetime
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
    def _validate_checkpoint_boundary(*, checkpoint_reason: str, node_id: str | None, node_attempt: int | None, node_status: str | None) -> None:
        """在 Durable Write 边界强制区分 Node-level 与 Execution-level Checkpoint。"""
        if checkpoint_reason == "frontier_completed":
            if node_id is not None or node_attempt is not None or node_status is not None:
                raise ValueError("frontier_completed Checkpoint 必须为 Execution-level boundary，不得携带 Node Fact")
        if checkpoint_reason == "node.completed" and node_id is None:
            raise ValueError("node.completed Checkpoint 必须携带 node_id")

    @staticmethod
    def _validate_execution_status_boundary(*, execution: WorkflowExecution, execution_status: str) -> None:
        """在 Durable Write 前确认 Checkpoint 快照没有跨越当前 Execution 生命周期。"""
        if execution.status != execution_status:
            raise HTTPException(409, f"Checkpoint Execution status 已变化: current={execution.status}, requested={execution_status}")

    @staticmethod
    def assert_node_fact_complete(*, checkpoint, node_execution) -> None:
        """验证带 Node 的 Checkpoint 与对应 NodeExecution 属于同一 Durable Fact。"""
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
    def _validate_worker_fencing(*, expected_worker_owner: str | None, expected_worker_attempt: int | None, execution: WorkflowExecution) -> None:
        """校验 Checkpoint 写入时的 Execution owner/generation/lease，阻断 stale Worker。"""
        if expected_worker_owner is None and expected_worker_attempt is None:
            return
        if expected_worker_owner is None or expected_worker_attempt is None:
            raise HTTPException(409, "Checkpoint Worker fencing 参数不完整")
        locked_attempt = int(execution.worker_attempt or 0)
        if execution.worker_owner != expected_worker_owner or locked_attempt != expected_worker_attempt:
            raise HTTPException(409, "Checkpoint Worker ownership 或 fencing generation 已失效")
        now = datetime.now(UTC).replace(tzinfo=None)
        if execution.worker_lease_expires_at is None or execution.worker_lease_expires_at <= now:
            raise HTTPException(409, "Checkpoint Worker lease 已失效")

    def _build(self, *, execution_id: UUID, frontier_id: UUID | None, sequence: int, execution_status: str, state_data: dict,
               checkpoint_reason: str, node_id: str | None = None, node_attempt: int | None = None,
               node_status: str | None = None, input_data: dict | None = None, output_data: dict | None = None,
               worker_owner: str | None = None, error_code: str | None = None, error_message: str | None = None) -> WorkflowExecutionCheckpoint:
        self._validate(sequence, checkpoint_reason)
        self._validate_checkpoint_boundary(checkpoint_reason=checkpoint_reason, node_id=node_id, node_attempt=node_attempt, node_status=node_status)
        return WorkflowExecutionCheckpoint(
            execution_id=execution_id, frontier_id=frontier_id, sequence=sequence, node_id=node_id,
            node_attempt=node_attempt, execution_status=execution_status, node_status=node_status,
            state_data=state_data, input_data=input_data, output_data=output_data,
            checkpoint_reason=checkpoint_reason, worker_owner=worker_owner,
            error_code=error_code, error_message=error_message,
        )

    async def append(self, *, execution_id: UUID, sequence: int, execution_status: str, state_data: dict,
                     checkpoint_reason: str, node_id: str | None = None, node_attempt: int | None = None,
                     node_status: str | None = None, input_data: dict | None = None, output_data: dict | None = None,
                     worker_owner: str | None = None, error_code: str | None = None,
                     error_message: str | None = None, tenant_id: UUID | None = None,
                     expected_worker_owner: str | None = None, expected_worker_attempt: int | None = None) -> WorkflowExecutionCheckpoint:
        """兼容旧调用方，但仍必须经过统一的 Execution Durable Write boundary。

        该入口不允许写入 `frontier_completed`，因为 Frontier completion 必须携带 source Frontier identity，
        并使用 `append_next_in_transaction()` 的调用方事务边界。普通 Checkpoint 则在此处锁定 Execution、
        校验 lifecycle / Worker fencing，并确认调用方提供的 sequence 正好是下一个 Durable sequence，
        防止旧入口绕过统一序号分配规则。
        """
        if checkpoint_reason == "frontier_completed":
            raise HTTPException(409, "frontier_completed Checkpoint 必须使用 append_next_in_transaction() 并绑定 source Frontier")
        self._validate(sequence, checkpoint_reason)
        self._validate_checkpoint_boundary(checkpoint_reason=checkpoint_reason, node_id=node_id, node_attempt=node_attempt, node_status=node_status)

        execution_query = select(WorkflowExecution).where(WorkflowExecution.id == execution_id).with_for_update()
        if tenant_id is not None:
            execution_query = execution_query.where(WorkflowExecution.tenant_id == tenant_id)
        execution_result = await self.db.execute(execution_query)
        execution = execution_result.scalar_one_or_none()
        if execution is None:
            raise HTTPException(409, f"Checkpoint 对应的 Workflow Execution 不存在或不属于当前 tenant: {execution_id}")
        self._validate_execution_status_boundary(execution=execution, execution_status=execution_status)
        self._validate_worker_fencing(expected_worker_owner=expected_worker_owner, expected_worker_attempt=expected_worker_attempt, execution=execution)

        latest_sequence = await self.db.execute(
            select(func.max(WorkflowExecutionCheckpoint.sequence)).where(WorkflowExecutionCheckpoint.execution_id == execution_id)
        )
        current_sequence = latest_sequence.scalar_one()
        expected_sequence = 0 if current_sequence is None else current_sequence + 1
        if sequence != expected_sequence:
            raise HTTPException(409, f"Checkpoint sequence 非当前 Execution 的下一个序号: expected={expected_sequence}, requested={sequence}")

        checkpoint = self._build(execution_id=execution_id, frontier_id=None, sequence=sequence,
                                 execution_status=execution_status, state_data=state_data,
                                 checkpoint_reason=checkpoint_reason, node_id=node_id, node_attempt=node_attempt,
                                 node_status=node_status, input_data=input_data, output_data=output_data,
                                 worker_owner=worker_owner, error_code=error_code, error_message=error_message)
        self.db.add(checkpoint)
        await self.db.commit()
        await self.db.refresh(checkpoint)
        return checkpoint

    async def append_next_in_transaction(self, *, execution_id: UUID, execution_status: str, state_data: dict,
                                         checkpoint_reason: str, node_id: str | None = None, node_attempt: int | None = None,
                                         node_status: str | None = None, input_data: dict | None = None,
                                         output_data: dict | None = None, worker_owner: str | None = None,
                                         error_code: str | None = None, error_message: str | None = None,
                                         tenant_id: UUID | None = None, expected_worker_owner: str | None = None,
                                         expected_worker_attempt: int | None = None, frontier_id: UUID | None = None) -> WorkflowExecutionCheckpoint:
        """在调用方事务中写入下一个 Checkpoint，并校验 tenant、Execution 生命周期与 Worker fencing generation。

        `frontier_id` 只用于把 `frontier_completed` Execution-level durable fact 绑定到其来源 Frontier；
        它不是 Node identity，不改变 Execution-level snapshot 的语义。历史未绑定的 completion fact 不会
        被猜测回填，避免多个并行 Frontier 共用同一 Execution 时把错误 Checkpoint 当成幂等事实。
        """
        self._validate(0, checkpoint_reason)
        self._validate_checkpoint_boundary(checkpoint_reason=checkpoint_reason, node_id=node_id, node_attempt=node_attempt, node_status=node_status)
        if checkpoint_reason == "frontier_completed" and frontier_id is None:
            raise HTTPException(409, "frontier_completed Checkpoint 必须绑定 source Frontier")
        if checkpoint_reason != "frontier_completed" and frontier_id is not None:
            raise HTTPException(409, "只有 frontier_completed Checkpoint 可以绑定 source Frontier")

        execution_query = select(WorkflowExecution).where(WorkflowExecution.id == execution_id).with_for_update()
        if tenant_id is not None:
            execution_query = execution_query.where(WorkflowExecution.tenant_id == tenant_id)
        execution_result = await self.db.execute(execution_query)
        execution = execution_result.scalar_one_or_none()
        if execution is None:
            raise HTTPException(409, f"Checkpoint 对应的 Workflow Execution 不存在或不属于当前 tenant: {execution_id}")
        self._validate_worker_fencing(expected_worker_owner=expected_worker_owner, expected_worker_attempt=expected_worker_attempt, execution=execution)

        if checkpoint_reason == "frontier_completed":
            boundary_result = await self.db.execute(
                select(WorkflowExecutionCheckpoint).where(
                    WorkflowExecutionCheckpoint.execution_id == execution_id,
                    WorkflowExecutionCheckpoint.frontier_id == frontier_id,
                    WorkflowExecutionCheckpoint.checkpoint_reason == "frontier_completed",
                ).order_by(desc(WorkflowExecutionCheckpoint.sequence))
            )
            existing_boundaries = list(boundary_result.scalars().all())
            if len(existing_boundaries) > 1:
                raise HTTPException(409, "同一 source Frontier 存在多个 completion Checkpoint，Durable fact 已分叉")
            if existing_boundaries:
                existing_boundary = existing_boundaries[0]
                if existing_boundary.execution_status != execution_status:
                    raise HTTPException(409, "同一 source Frontier 的 completion Checkpoint lifecycle 与本次写入不一致，拒绝产生第二条 Durable fact")
                if existing_boundary.state_data != state_data:
                    raise HTTPException(409, "同一 source Frontier 的 completion Checkpoint payload 与本次写入不一致，拒绝产生第二条 Durable fact")
                return existing_boundary

        self._validate_execution_status_boundary(execution=execution, execution_status=execution_status)
        latest_sequence = await self.db.execute(
            select(func.max(WorkflowExecutionCheckpoint.sequence)).where(WorkflowExecutionCheckpoint.execution_id == execution_id)
        )
        current_sequence = latest_sequence.scalar_one()
        sequence = 0 if current_sequence is None else current_sequence + 1
        checkpoint = self._build(execution_id=execution_id, frontier_id=frontier_id, sequence=sequence,
                                 execution_status=execution_status, state_data=state_data,
                                 checkpoint_reason=checkpoint_reason, node_id=node_id, node_attempt=node_attempt,
                                 node_status=node_status, input_data=input_data, output_data=output_data,
                                 worker_owner=worker_owner, error_code=error_code, error_message=error_message)
        self.db.add(checkpoint)
        await self.db.flush()
        return checkpoint

    async def latest(self, execution_id: UUID, *, tenant_id: UUID | None = None) -> WorkflowExecutionCheckpoint | None:
        query = select(WorkflowExecutionCheckpoint).join(WorkflowExecution, WorkflowExecution.id == WorkflowExecutionCheckpoint.execution_id).where(WorkflowExecutionCheckpoint.execution_id == execution_id)
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
            node_query = select(WorkflowNodeExecution).join(WorkflowExecution, WorkflowExecution.id == WorkflowNodeExecution.execution_id).where(
                WorkflowNodeExecution.execution_id == execution_id, WorkflowNodeExecution.node_id == checkpoint.node_id,
            )
            if tenant_id is not None:
                node_query = node_query.where(WorkflowExecution.tenant_id == tenant_id)
            result = await self.db.execute(node_query)
            node_execution = result.scalar_one_or_none()
        self.assert_node_fact_complete(checkpoint=checkpoint, node_execution=node_execution)
        return checkpoint
