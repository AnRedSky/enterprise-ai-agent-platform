"""Workflow Runtime 的 DAG Join 扩展入口。

本模块只补充 Join Node 的 Runtime 语义，不复制基础 Runtime 的 Retry、Timeout、CircuitBreaker、
NodeExecution 或 Checkpoint 逻辑。基础执行仍委托 `runtime.WorkflowRuntime`。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from app.runtime.workflow.runtime import WorkflowRuntime as BaseWorkflowRuntime
from app.services.workflow.checkpoint.recovery.dag_join import WorkflowDagJoinReadinessService


class WorkflowRuntime(BaseWorkflowRuntime):
    """支持 DAG Join Node 的 Workflow Runtime。

    Join 是纯状态汇聚节点：其输入必须来自已经持久化完成的 predecessor output，
    不触发模型 Provider。真正的 NodeExecution / Checkpoint 仍复用基础 Runtime 的
    `_execute_node_with_policy()` 和 WorkflowExecutionService.transition_node()。
    """

    NODE_TYPES = BaseWorkflowRuntime.NODE_TYPES | {"join"}

    @staticmethod
    def _join_predecessors(definition: dict, node_id: str) -> tuple[str, ...]:
        return tuple(sorted(
            edge.get("source")
            for edge in definition.get("edges", []) or []
            if isinstance(edge, dict)
            and edge.get("target") == node_id
            and isinstance(edge.get("source"), str)
        ))

    @staticmethod
    def _is_join_node(definition: dict, node_id: str) -> bool:
        return any(
            isinstance(node, dict)
            and node.get("id") == node_id
            and node.get("type") == "join"
            for node in definition.get("nodes", [])
        )

    async def _resolve_resume_context(self, execution, definition: dict, state_data: dict):
        """Resume 时将 Join frontier 接入正式 Readiness Contract。"""
        context = await super()._resolve_resume_context(execution, definition, state_data)
        if context is None:
            return None
        plan, branch_state_data = context
        if len(plan.frontier_node_ids) != 1:
            return context

        node_id = plan.frontier_node_ids[0]
        if not self._is_join_node(definition, node_id):
            return context
        if len(self._join_predecessors(definition, node_id)) < 2:
            return context

        source_nodes = await self._load_completed_resume_nodes(execution)
        node_outputs: Mapping[str, Mapping[str, object]] = {
            node.node_id: dict(node.output_data or {})
            for node in source_nodes
            if isinstance(node.output_data, dict)
        }
        completed_node_ids = {node.node_id for node in source_nodes}
        readiness = WorkflowDagJoinReadinessService.evaluate(
            definition=definition,
            node_id=node_id,
            completed_node_ids=completed_node_ids,
            node_outputs=node_outputs,
        )
        if not readiness.ready or readiness.state_data is None:
            return context
        return (
            replace(plan, state_data=dict(readiness.state_data)),
            {node_id: dict(readiness.state_data)},
        )

    async def execute_node(self, node: dict, input_data: dict, actor_id, is_admin: bool,
                           session_id, tenant_id=None, execution=None) -> dict:
        """Join Node 为纯状态汇聚节点；其它 Node 继续走基础 Runtime。"""
        if node.get("type") == "join":
            return dict(input_data)
        return await super().execute_node(
            node,
            input_data,
            actor_id,
            is_admin,
            session_id,
            tenant_id,
            execution=execution,
        )
