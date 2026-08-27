"""Workflow Runtime 的 DAG Join 扩展入口。

本模块只补充 Join Node 的 Runtime 语义与 Recovery Trace Continuity，不复制基础 Runtime 的 Retry、Timeout、CircuitBreaker、NodeExecution 或 Checkpoint 逻辑。
边界：Join 只消费已经持久化完成的 predecessor output；Runtime Trace 只恢复已有 Recovery trace identity，不携带业务 state。
关键依赖：基础 WorkflowRuntime、WorkflowDagJoinReadinessService、WorkflowRecoveryTraceLinkService、WorkflowRecoveryTelemetry。
"""

from __future__ import annotations

from dataclasses import replace
from time import monotonic
from typing import Mapping

from app.runtime.workflow.runtime import WorkflowRuntime as BaseWorkflowRuntime
from app.services.workflow.checkpoint.recovery.dag_join import WorkflowDagJoinReadinessService
from app.services.workflow.checkpoint.recovery.observability import (
    WorkflowRecoveryEvent,
    WorkflowRecoveryTelemetry,
)
from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


class WorkflowRuntime(BaseWorkflowRuntime):
    """支持 DAG Join Node 与 Recovery Trace Continuity 的 Workflow Runtime。

    Join 是纯状态汇聚节点：其输入必须来自已经持久化完成的 predecessor output，不触发模型 Provider。
    Recovery Resume Runtime 继续复用基础 Runtime 的 Retry、Timeout、Checkpoint 与 Worker ownership 边界。
    """

    NODE_TYPES = BaseWorkflowRuntime.NODE_TYPES | {"join"}

    @staticmethod
    def _join_predecessors(definition: dict, node_id: str) -> tuple[str, ...]:
        """返回 Join Node 的确定性 predecessor 列表。

        Args:
            definition: 已冻结并通过校验的 Workflow Definition。
            node_id: Join Node ID。

        Returns:
            按 Node ID 排序的 predecessor ID 元组。
        """
        return tuple(sorted(
            edge.get("source")
            for edge in definition.get("edges", []) or []
            if isinstance(edge, dict)
            and edge.get("target") == node_id
            and isinstance(edge.get("source"), str)
        ))

    @staticmethod
    def _is_join_node(definition: dict, node_id: str) -> bool:
        """判断指定 Node 是否明确声明为 Join 类型。

        Args:
            definition: Workflow Definition。
            node_id: 待判断的 Node ID。

        Returns:
            Node 明确为 `join` 时返回 True，否则返回 False。
        """
        return any(
            isinstance(node, dict)
            and node.get("id") == node_id
            and node.get("type") == "join"
            for node in definition.get("nodes", [])
        )

    async def _resolve_resume_context(self, execution, definition: dict, state_data: dict):
        """Resume 时将 Join frontier 接入正式 Readiness Contract。

        Args:
            execution: 当前 Resume Execution。
            definition: 当前 Workflow Version Definition。
            state_data: Resume Execution 输入状态，仅作为基础 Contract 的兼容输入。

        Returns:
            基础 Resume context，Join frontier 会替换为由持久化 predecessor output 合并得到的状态。

        Raises:
            HTTPException: 基础 Resume Contract 或 Join State Merge Contract 不满足时向上层传播。
        """
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
        """Join Node 为纯状态汇聚节点；其它 Node 继续走基础 Runtime。

        Args:
            node: 当前 Workflow Node 定义。
            input_data: 已由 Resume Planner / Join Readiness 验证的输入状态。
            actor_id: 当前执行身份。
            is_admin: 是否使用管理员权限。
            session_id: 当前 Execution ID。
            tenant_id: 当前租户 ID。
            execution: 当前 Workflow Execution。

        Returns:
            Join 返回独立状态副本；其它 Node 返回基础 Runtime 执行结果。
        """
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

    async def execute(self, execution, version, actor_id, is_admin: bool = False,
                      allow_legacy_empty_nodes: bool = False) -> dict:
        """执行 Workflow，并在 Recovery Resume 场景把持久化 trace_id 延续到 Runtime。

        Args:
            execution: 当前待执行的 Workflow Execution。
            version: 当前 Workflow Version。
            actor_id: Runtime 执行身份。
            is_admin: 是否使用管理员权限执行 Agent Node。
            allow_legacy_empty_nodes: 是否允许历史空节点兼容模式。

        Returns:
            基础 WorkflowRuntime 返回的最终执行状态。

        Raises:
            Exception: 基础 Runtime 的业务异常原样向 Worker / ExecutionService 传播。

        设计意图：Worker 与 Recovery 进程可能已经退出，Runtime 必须从持久化 Trace Link 恢复同一 trace_id；
        Runtime 只发控制面 started/finished 事件，不读取或复制 Trace Link 的业务 payload。
        """
        trace_link = WorkflowRecoveryTraceLinkService(self.db)
        trace_id = await trace_link.get_trace_id(execution)
        if trace_id is None:
            return await super().execute(
                execution,
                version,
                actor_id,
                is_admin,
                allow_legacy_empty_nodes=allow_legacy_empty_nodes,
            )

        telemetry = WorkflowRecoveryTelemetry()
        started = monotonic()
        telemetry.emit(
            WorkflowRecoveryEvent(
                event_name="workflow.recovery.runtime.started",
                execution_id=execution.id,
                resume_execution_id=execution.id,
                trace_id=trace_id,
                phase="runtime",
            )
        )
        outcome = "completed"
        reason_code = None
        try:
            return await super().execute(
                execution,
                version,
                actor_id,
                is_admin,
                allow_legacy_empty_nodes=allow_legacy_empty_nodes,
            )
        except Exception as exc:
            outcome = "failed"
            reason_code = type(exc).__name__
            raise
        finally:
            telemetry.emit(
                WorkflowRecoveryEvent(
                    event_name="workflow.recovery.runtime.finished",
                    execution_id=execution.id,
                    resume_execution_id=execution.id,
                    trace_id=trace_id,
                    outcome=outcome,
                    reason_code=reason_code,
                    phase="runtime",
                    duration_ms=(monotonic() - started) * 1000,
                )
            )
