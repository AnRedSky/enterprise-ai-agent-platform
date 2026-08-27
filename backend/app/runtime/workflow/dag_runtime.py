"""Workflow Runtime DAG 编排扩展入口。

职责：在基础 WorkflowRuntime 上接入 Join Node、Conditional DAG 首次执行的多根 frontier 初始化，以及 Recovery Trace Continuity。
边界：不复制基础 Runtime 的 Retry、Timeout、Checkpoint、ownership 或模型调用逻辑；条件规则仍由 Condition Evaluator / DAG Planner 负责。
关键依赖：基础 WorkflowRuntime、WorkflowDagContractValidator、WorkflowDagResumePlanner、WorkflowDagResumeRuntimePlanner、WorkflowRecoveryTraceLinkService。
"""

from __future__ import annotations

from time import monotonic

from fastapi import HTTPException

from app.runtime.workflow.runtime import WorkflowRuntime as BaseWorkflowRuntime
from app.services.workflow.checkpoint.recovery import WorkflowDagContractValidator, WorkflowDagResumePlanner
from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlanner
from app.services.workflow.checkpoint.recovery.observability import WorkflowRecoveryEvent, WorkflowRecoveryTelemetry
from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


class WorkflowRuntime(BaseWorkflowRuntime):
    """支持 Join、Conditional DAG 初始化与 Recovery Trace Continuity 的 Workflow Runtime。"""

    NODE_TYPES = BaseWorkflowRuntime.NODE_TYPES | {"join"}

    @classmethod
    def validate_definition(cls, definition: dict, *, allow_legacy_empty_nodes: bool = False) -> list[dict]:
        """校验基础 Runtime Definition，并在存在 edges 时冻结 DAG / Conditional Contract。

        Args:
            definition: Workflow Version Definition。
            allow_legacy_empty_nodes: 是否允许历史空节点兼容模式。

        Returns:
            基础 Runtime 标准化后的 Node Definition。

        Raises:
            HTTPException: 基础 Runtime 或 DAG / Condition Contract 不满足要求时抛出。
        """
        nodes = super().validate_definition(definition, allow_legacy_empty_nodes=allow_legacy_empty_nodes)
        if "edges" in definition:
            try:
                WorkflowDagContractValidator.validate(definition=definition)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
        return nodes

    async def _resolve_dag_context(self, execution, definition: dict, state_data: dict):
        """统一解析首次执行与 Resume 的 DAG frontier，并为多根首次执行初始化独立分支状态。

        Args:
            execution: 当前 Workflow Execution。
            definition: 已冻结的 Workflow Version Definition。
            state_data: 当前执行输入状态。

        Returns:
            `(plan, branch_state_data)`；没有 DAG edges 时返回 None。

        Raises:
            HTTPException: DAG Contract、条件状态或 Runtime Plan 不满足要求。

        设计意图：首次执行与 Resume 必须使用同一个 DAG Planner；首次执行如果存在多个 root，所有 root 共享同一输入快照，但随后各自进入独立 frontier state，不能因为没有 completed Node 就退回顺序执行。
        """
        if not definition.get("edges"):
            return None

        source_nodes = await self._load_completed_resume_nodes(execution)
        completed_node_ids = {node.node_id for node in source_nodes}
        state_data_by_node = {node.node_id: dict(node.output_data or {}) for node in source_nodes}
        try:
            plan = WorkflowDagResumePlanner.plan(
                definition=definition,
                completed_node_ids=completed_node_ids,
                state_data_by_node=state_data_by_node,
            )
            if not completed_node_ids:
                branch_state_data = {node_id: dict(state_data) for node_id in plan.frontier_node_ids}
            else:
                branch_state_data = self._build_frontier_branch_states(
                    definition,
                    plan.frontier_node_ids,
                    source_nodes,
                    plan.selected_predecessor_node_ids,
                ) if plan.frontier_node_ids else {}
            runtime_plan = WorkflowDagResumeRuntimePlanner.plan(
                definition=definition,
                completed_node_ids=completed_node_ids,
                state_data=state_data,
                branch_state_data=branch_state_data if len(plan.frontier_node_ids) > 1 else None,
                state_data_by_node=state_data_by_node,
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return runtime_plan, branch_state_data

    async def execute_node(self, node: dict, input_data: dict, actor_id, is_admin: bool,
                           session_id, tenant_id=None, execution=None) -> dict:
        """执行 Join Node 或委托其它 Node 给基础 Runtime。

        Args:
            node: 当前 Workflow Node Definition。
            input_data: 当前 Node 输入状态。
            actor_id: Runtime 执行身份。
            is_admin: 是否使用管理员权限。
            session_id: 当前 Execution ID。
            tenant_id: 当前租户范围。
            execution: 当前 Workflow Execution。

        Returns:
            Node 输出状态；Join Node 原样返回输入状态。
        """
        if node.get("type") == "join":
            return dict(input_data)
        return await super().execute_node(node, input_data, actor_id, is_admin, session_id, tenant_id, execution=execution)

    async def execute(self, execution, version, actor_id, is_admin: bool = False,
                      allow_legacy_empty_nodes: bool = False) -> dict:
        """执行 Workflow，并在 Recovery Resume 场景延续持久化 trace_id。

        Args:
            execution: 当前待执行的 Workflow Execution。
            version: 当前 Workflow Version。
            actor_id: Runtime 执行身份。
            is_admin: 是否使用管理员权限执行 Agent Node。
            allow_legacy_empty_nodes: 是否允许历史空节点兼容模式。

        Returns:
            Workflow 最终执行状态。

        设计边界：Trace Continuity 只负责恢复链路观测，不复制基础 Runtime 的执行、Checkpoint 或状态机逻辑。
        """
        trace_link = WorkflowRecoveryTraceLinkService(self.db)
        trace_id = await trace_link.get_trace_id(execution)
        if trace_id is None:
            return await super().execute(execution, version, actor_id, is_admin, allow_legacy_empty_nodes=allow_legacy_empty_nodes)
        telemetry = WorkflowRecoveryTelemetry()
        started = monotonic()
        telemetry.emit(WorkflowRecoveryEvent(
            event_name="workflow.recovery.runtime.started",
            execution_id=execution.id,
            resume_execution_id=execution.id,
            trace_id=trace_id,
            phase="runtime",
        ))
        outcome = "completed"
        reason_code = None
        try:
            return await super().execute(execution, version, actor_id, is_admin, allow_legacy_empty_nodes=allow_legacy_empty_nodes)
        except Exception as exc:
            outcome = "failed"
            reason_code = type(exc).__name__
            raise
        finally:
            telemetry.emit(WorkflowRecoveryEvent(
                event_name="workflow.recovery.runtime.finished",
                execution_id=execution.id,
                resume_execution_id=execution.id,
                trace_id=trace_id,
                outcome=outcome,
                reason_code=reason_code,
                phase="runtime",
                duration_ms=(monotonic() - started) * 1000,
            ))
