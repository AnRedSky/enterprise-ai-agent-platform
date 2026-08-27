"""Workflow DAG Join Node 执行协调模块。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.services.workflow.checkpoint.recovery.dag_join import WorkflowDagJoinReadiness

JoinNodeExecutor = Callable[[dict], Awaitable[dict]]
JoinNodePersister = Callable[[str, dict], Awaitable[None]]


@dataclass(frozen=True)
class WorkflowDagJoinExecutionResult:
    """Join Node 一次协调执行的确定性结果。"""

    node_id: str
    executed: bool
    state_data: dict


class WorkflowDagJoinExecutor:
    """执行已 ready 的 Join Node，并把持久化委托给既有 ExecutionService。"""

    @staticmethod
    async def execute(
        readiness: WorkflowDagJoinReadiness,
        *,
        node: dict,
        executor: JoinNodeExecutor,
        persister: JoinNodePersister | None = None,
        already_completed: bool = False,
    ) -> WorkflowDagJoinExecutionResult:
        """执行 Join；已完成事实可直接收敛，避免重复调用 Node。"""
        if not isinstance(node, dict):
            raise ValueError("DAG Join Node 必须为对象")
        node_id = node.get("id")
        if node_id != readiness.node_id:
            raise ValueError("DAG Join Node 与 readiness node_id 不一致")
        if already_completed:
            if readiness.state_data is None:
                raise ValueError("已完成 Join Node 必须存在持久化 state")
            return WorkflowDagJoinExecutionResult(
                node_id=node_id,
                executed=False,
                state_data=deepcopy(readiness.state_data),
            )
        if not readiness.ready or readiness.state_data is None:
            raise ValueError(f"DAG Join Node {node_id} 尚未 ready")

        output = await executor(deepcopy(readiness.state_data))
        if not isinstance(output, dict):
            raise ValueError(f"DAG Join Node {node_id} 执行结果必须为对象")
        output_copy = deepcopy(output)
        if persister is not None:
            await persister(node_id, deepcopy(output_copy))
        return WorkflowDagJoinExecutionResult(
            node_id=node_id,
            executed=True,
            state_data=output_copy,
        )
