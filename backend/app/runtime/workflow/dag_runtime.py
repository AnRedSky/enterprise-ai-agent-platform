"""Workflow Runtime 的 DAG Join 与 Conditional Branching 扩展入口。

职责：在基础 WorkflowRuntime 上接入 Join、Conditional Branching 与 Recovery Trace Continuity。
边界：不复制基础 Runtime 的 Retry、Timeout、Checkpoint、ownership 或模型调用逻辑；条件规则只由 Condition Evaluator / DAG Planner 负责。
关键依赖：基础 WorkflowRuntime、WorkflowDagContractValidator、WorkflowDagResumePlanner、WorkflowDagJoinReadinessService、WorkflowRecoveryTraceLinkService。
"""

from __future__ import annotations

from dataclasses import replace
from time import monotonic
from typing import Mapping

from fastapi import HTTPException

from app.runtime.workflow.runtime import WorkflowRuntime as BaseWorkflowRuntime
from app.services.workflow.checkpoint.recovery import WorkflowDagContractValidator, WorkflowDagJoinReadinessService, WorkflowDagResumePlanner
from app.services.workflow.checkpoint.recovery.dag_state_merge import WorkflowDagBranchState, WorkflowDagBranchStateMergeService
from app.services.workflow.checkpoint.recovery.observability import WorkflowRecoveryEvent, WorkflowRecoveryTelemetry
from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


class WorkflowRuntime(BaseWorkflowRuntime):
    """支持 DAG Join、Conditional Branching 与 Recovery Trace Continuity 的 Workflow Runtime。"""

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

    @staticmethod
    def _is_join_node(definition: dict, node_id: str) -> bool:
        """判断指定 Node 是否明确声明为 Join 类型。

        Args:
            definition: Workflow Definition。
            node_id: 待判断的 Node ID。

        Returns:
            Node 明确为 `join` 时返回 True，否则返回 False。
        """
        return any(isinstance(node, dict) and node.get("id") == node_id and node.get("type") == "join" for node in definition.get("nodes", []))

    @staticmethod
    def _selected_predecessors(plan, node_id: str) -> tuple[str, ...]:
        """读取 Planner 已确定的有效 predecessor，不重新解释条件边。

        Args:
            plan: WorkflowDagResumeRuntimePlan。
            node_id: 当前 frontier Node ID。

        Returns:
            Planner 已选中的 predecessor ID 元组。
        """
        return dict(plan.selected_predecessor_node_ids).get(node_id, ())

    @staticmethod
    def _build_frontier_branch_states(frontier_node_ids: tuple[str, ...], source_nodes, selected_predecessors: Mapping[str, tuple[str, ...]]) -> dict[str, dict]:
        """按 Planner 选中的 predecessor 输出构造独立 Branch state。

        Args:
            frontier_node_ids: 当前 frontier Node ID。
            source_nodes: 从持久化事实读取的已完成 Node Execution。
            selected_predecessors: Planner 为每个 target 选择的有效 predecessor。

        Returns:
            每个 frontier Node 的状态快照。

        Raises:
            ValueError: 有效 predecessor 缺少持久化输出。
        """
        source_by_id = {node.node_id: dict(node.output_data or {}) for node in source_nodes}
        result: dict[str, dict] = {}
        for node_id in frontier_node_ids:
            predecessors = selected_predecessors.get(node_id, ())
            if not predecessors:
                raise ValueError(f"DAG Resume frontier {node_id} 缺少已完成 predecessor state")
            states = []
            for predecessor_id in predecessors:
                if predecessor_id not in source_by_id:
                    raise ValueError(f"DAG Resume frontier {node_id} 缺少已完成 predecessor state")
                states.append(source_by_id[predecessor_id])
            if len(states) == 1:
                result[node_id] = states[0]
            else:
                result[node_id] = WorkflowDagBranchStateMergeService.merge(tuple(
                    WorkflowDagBranchState(node_id=f"{node_id}:predecessor:{index}", state_data=state)
                    for index, state in enumerate(states)
                )).state_data
        return result

    async def _resolve_resume_context(self, execution, definition: dict, state_data: dict):
        """从持久化完成事实重新计算 Conditional frontier，并接入 Join Readiness。

        Args:
            execution: 当前 Resume Execution。
            definition: 当前 Workflow Version Definition。
            state_data: Resume Execution 输入状态。

        Returns:
            `(plan, branch_state_data)`；非 Resume Execution 返回 None。

        Raises:
            HTTPException: 持久化完成事实、Condition、DAG 或 Join Contract 不满足时抛出。
        """
        if getattr(execution, "resume_of_execution_id", None) is None:
            return None
        source_nodes = await self._load_completed_resume_nodes(execution)
        completed_node_ids = {node.node_id for node in source_nodes}
        state_data_by_node: dict[str, Mapping[str, object]] = {
            node.node_id: dict(node.output_data or {}) for node in source_nodes if isinstance(node.output_data, dict)
        }
        try:
            frontier = WorkflowDagResumePlanner.plan(
                definition=definition,
                completed_node_ids=completed_node_ids,
                state_data_by_node=state_data_by_node,
            )
            selected_predecessors = dict(frontier.selected_predecessor_node_ids)
            branch_state_data = self._build_frontier_branch_states(
                frontier.frontier_node_ids,
                source_nodes,
                selected_predecessors,
            ) if frontier.frontier_node_ids else {}
            plan = self._build_resume_runtime_plan(
                definition=definition,
                completed_node_ids=completed_node_ids,
                state_data=state_data,
                branch_state_data=branch_state_data if len(frontier.frontier_node_ids) > 1 else None,
                state_data_by_node=state_data_by_node,
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

        if len(plan.frontier_node_ids) != 1:
            return plan, branch_state_data
        node_id = plan.frontier_node_ids[0]
        if not self._is_join_node(definition, node_id):
            return plan, branch_state_data
        predecessors = self._selected_predecessors(plan, node_id)
        if len(predecessors) < 2:
            return plan, branch_state_data
        node_outputs: Mapping[str, Mapping[str, object]] = {
            node.node_id: dict(node.output_data or {}) for node in source_nodes if isinstance(node.output_data, dict)
        }
        readiness = WorkflowDagJoinReadinessService.evaluate(
            definition=definition,
            node_id=node_id,
            completed_node_ids=completed_node_ids,
            node_outputs=node_outputs,
            predecessor_node_ids=predecessors,
        )
        if not readiness.ready or readiness.state_data is None:
            return plan, branch_state_data
        return replace(plan, state_data=dict(readiness.state_data)), {node_id: dict(readiness.state_data)}

    def _build_resume_runtime_plan(self, *, definition, completed_node_ids, state_data, branch_state_data, state_data_by_node):
        """通过现有 Runtime Planner 生成 Conditional Resume 计划，避免建立第二套 Runtime 规划器。

        Args:
            definition: Workflow Version Definition。
            completed_node_ids: 已完成 Node 集合。
            state_data: 当前 Resume 输入状态。
            branch_state_data: 多 frontier 分支状态。
            state_data_by_node: 已完成 Node 持久化输出。

        Returns:
            现有 WorkflowDagResumeRuntimePlanner 生成的 Runtime Plan。
        """
        from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlanner
        return WorkflowDagResumeRuntimePlanner.plan(
            definition=definition,
            completed_node_ids=completed_node_ids,
            state_data=state_data,
            branch_state_data=branch_state_data,
            state_data_by_node=state_data_by_node,
        )

    async def execute_node(self, node: dict, input_data: dict, actor_id, is_admin: bool,
                           session_id, tenant_id=None, execution=None) -> dict:
        """Join Node 为纯状态汇聚节点；其它 Node 继续走基础 Runtime。"""
        if node.get("type") == "join":
            return dict(input_data)
        return await super().execute_node(node, input_data, actor_id, is_admin, session_id, tenant_id, execution=execution)

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
        """
        trace_link = WorkflowRecoveryTraceLinkService(self.db)
        trace_id = await trace_link.get_trace_id(execution)
        if trace_id is None:
            return await super().execute(execution, version, actor_id, is_admin, allow_legacy_empty_nodes=allow_legacy_empty_nodes)
        telemetry = WorkflowRecoveryTelemetry()
        started = monotonic()
        telemetry.emit(WorkflowRecoveryEvent(event_name="workflow.recovery.runtime.started", execution_id=execution.id, resume_execution_id=execution.id, trace_id=trace_id, phase="runtime"))
        outcome = "completed"
        reason_code = None
        try:
            return await super().execute(execution, version, actor_id, is_admin, allow_legacy_empty_nodes=allow_legacy_empty_nodes)
        except Exception as exc:
            outcome = "failed"
            reason_code = type(exc).__name__
            raise
        finally:
            telemetry.emit(WorkflowRecoveryEvent(event_name="workflow.recovery.runtime.finished", execution_id=execution.id, resume_execution_id=execution.id, trace_id=trace_id, outcome=outcome, reason_code=reason_code, phase="runtime", duration_ms=(monotonic() - started) * 1000))
