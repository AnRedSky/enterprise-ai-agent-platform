"""Workflow Checkpoint 服务正式导出入口。

保持 CheckpointService 的唯一持久化实现，同时在领域导出层规范手动执行的
``worker_owner=None`` fencing 参数：非 Worker 执行没有 fencing generation，
不能把默认的 ``worker_attempt=0`` 误判成不完整的 Worker fencing。
"""

from app.services.workflow.checkpoint.recovery import (
    WorkflowExecutionCheckpointRecoveryService,
    WorkflowExecutionResumeAssessment,
)
from app.services.workflow.checkpoint.service import (
    WorkflowExecutionCheckpointService as _WorkflowExecutionCheckpointService,
)


class WorkflowExecutionCheckpointService(_WorkflowExecutionCheckpointService):
    """统一规范 Worker 与手动执行的 Checkpoint fencing 输入。"""

    async def append_next_in_transaction(self, **kwargs):
        """手动执行不携带 Worker fencing generation；Worker 执行保持原校验。"""
        if kwargs.get("expected_worker_owner") is None and kwargs.get("expected_worker_attempt") == 0:
            kwargs["expected_worker_attempt"] = None
        return await super().append_next_in_transaction(**kwargs)


__all__ = [
    "WorkflowExecutionCheckpointService",
    "WorkflowExecutionCheckpointRecoveryService",
    "WorkflowExecutionResumeAssessment",
]
