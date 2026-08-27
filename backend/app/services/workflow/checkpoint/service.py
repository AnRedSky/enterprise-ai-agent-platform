"""Workflow Execution Checkpoint 领域服务。"""

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
        self._validate(0, checkpoint_reason)
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
