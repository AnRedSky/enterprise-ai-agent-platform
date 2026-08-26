"""Workflow Execution Checkpoint 领域服务。

负责将 Execution 在明确边界上的状态快照追加到 PostgreSQL，并读取最新检查点。
本服务不执行 Runtime、不改变 Execution/Node 状态机，也不绕过 Worker ownership fencing。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint


class WorkflowExecutionCheckpointService:
    """负责 Workflow Execution Checkpoint 的持久化边界。"""

    def __init__(self, db: AsyncSession) -> None:
        """初始化 Checkpoint 服务。

        Args:
            db: 用于保存和读取 Checkpoint 的异步数据库会话。
        """
        self.db = db

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
        """追加不可变 Checkpoint。

        Args:
            execution_id: 对应 Workflow Execution ID。
            sequence: Execution 内单调递增的 Checkpoint 序号，由调用边界负责分配。
            execution_status: 写入快照时的 Execution 状态。
            state_data: 可用于后续恢复的业务状态快照。
            checkpoint_reason: 产生快照的原因，例如 `node.completed` 或 `execution.failed`。
            node_id: 当前 Node ID，可为空。
            node_attempt: 当前 Node attempt，可为空。
            node_status: 当前 Node 状态，可为空。
            input_data: 当前 Node 输入快照，可为空。
            output_data: 当前 Node 输出快照，可为空。
            worker_owner: 创建快照的 Worker owner，可为空。
            error_code: 当前错误码，可为空。
            error_message: 当前错误消息，可为空。

        Returns:
            已持久化的不可变 Checkpoint。

        Raises:
            IntegrityError: `execution_id + sequence` 已存在时拒绝覆盖历史快照。

        事务边界：服务只负责追加对象并提交当前事务，不创建独立事务，也不负责跨 Runtime 状态转换。
        """
        if sequence < 0:
            raise ValueError("Checkpoint sequence 必须大于等于 0")
        if not checkpoint_reason.strip():
            raise ValueError("Checkpoint reason 不能为空")

        checkpoint = WorkflowExecutionCheckpoint(
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
        self.db.add(checkpoint)
        await self.db.commit()
        await self.db.refresh(checkpoint)
        return checkpoint

    async def latest(self, execution_id: UUID) -> WorkflowExecutionCheckpoint | None:
        """读取 Execution 最新的 Checkpoint。

        Args:
            execution_id: 对应 Workflow Execution ID。

        Returns:
            按 `sequence` 降序取得的最新 Checkpoint，不存在时返回 `None`。
        """
        result = await self.db.execute(
            select(WorkflowExecutionCheckpoint)
            .where(WorkflowExecutionCheckpoint.execution_id == execution_id)
            .order_by(desc(WorkflowExecutionCheckpoint.sequence))
            .limit(1)
        )
        return result.scalar_one_or_none()
