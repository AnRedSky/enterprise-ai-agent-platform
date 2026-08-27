"""Workflow Runtime DAG 编排扩展入口。

职责：在基础 WorkflowRuntime 上接入 Join Node、Conditional DAG 首次执行的多根 frontier 初始化，以及 Recovery Trace Continuity。
边界：不复制基础 Runtime 的 Retry、Timeout、Checkpoint、ownership 或模型调用逻辑；条件规则仍由 Condition Evaluator / DAG Planner 负责。
关键依赖：基础 WorkflowRuntime、WorkflowDagContractValidator、WorkflowDagResumePlanner、WorkflowDagResumeRuntimePlanner、WorkflowRecoveryTraceLinkService。
"""

from __future__ import annotations

from time import monotonic

from fastapi import HTTPException
from sqlalchemy import select

from app.models.workflow_execution import WorkflowNodeExecution
from app.runtime.workflow.runtime import WorkflowRuntime as BaseWorkflowRuntime
from app.services.workflow.checkpoint.recovery import WorkflowDagContractValidator, WorkflowDagResumePlanner
from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlanner
from app.services.workflow.checkpoint.recovery.observability import WorkflowRecoveryEvent, WorkflowRecoveryTelemetry
from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


class WorkflowRuntime(BaseWorkflowRuntime):
    """支持 Join、Conditional DAG 初始化与 Recovery Trace Continuity 的 Workflow Runtime。"""

    NODE_TYPES = BaseWorkflowRuntime.NODE_TYPES | {"join"}
    DAG_DECISION_EVENT = "workflow.dag.frontier_decided"

    @classmethod
    def validate_definition(cls, definition: dict, *, allow_legacy_empty_nodes: bool = False) -> list[dict]:
        """校验基础 Runtime Definition，并在存在 edges 时冻结 DAG / Conditional Contract。"""
        nodes = super().validate_definition(definition, allow_legacy_empty_nodes=allow_legacy_empty_nodes)
        if "edges" in definition:
            try:
                WorkflowDagContractValidator.validate(definition=definition)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
        return nodes

    async def _load_completed_resume_nodes(self, execution) -> list[WorkflowNodeExecution]:
        """读取当前 Execution 与 Resume Source 的完成事实。

        Args:
            execution: 当前 Workflow Execution。

        Returns:
            当前 Execution 与 Resume Source 的已完成 NodeExecution。

        设计意图：NodeExecution 表没有独立 tenant_id 列，tenant boundary 已由关联的 Execution 身份确定；
        因此这里必须按 execution_id 收敛事实，不能引用不存在的 NodeExecution.tenant_id 字段。
        """
        execution_ids = [execution.id]
        source_execution_id = getattr(execution, "resume_of_execution_id", None)
        if source_execution_id is not None:
            execution_ids.insert(0, source_execution_id)
        query = select(WorkflowNodeExecution).where(
            WorkflowNodeExecution.execution_id.in_(execution_ids),
            WorkflowNodeExecution.status == "completed",
        ).order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc())
        return list((await self.db.execute(query)).scalars().all())

    async def _record_dag_frontier_decision(self, execution, version_definition: dict, plan, actor_id, trace_link=None) -> None:
        """将 Planner 的确定性 decision fingerprint 持久化为可审计 Trace fact，并校验 replay 一致性。"""
        if self.execution_service is None or execution is None:
            return
        completed = list(plan.completed_node_ids)
        frontier = list(plan.frontier_node_ids)
        selected = [
            {"node_id": node_id, "predecessor_node_ids": list(predecessors)}
            for node_id, predecessors in plan.selected_predecessor_node_ids
        ]
        decision_id = plan.decision_fingerprint
        if not decision_id:
            raise ValueError("DAG Resume Planner 未生成 decision fingerprint")

        trace_link = trace_link or WorkflowRecoveryTraceLinkService(self.db)
        trace_id = await trace_link.get_trace_id(execution)
        if trace_id is not None:
            await trace_link.assert_dag_decision_replay_consistent(
                execution,
                trace_id,
                completed,
                decision_id,
                frontier,
                selected,
            )
            await trace_link.record_dag_decision(
                execution,
                trace_id,
                actor_id or execution.created_by,
                decision_id,
                completed,
                frontier,
                selected,
            )
            return

        await self.execution_service.governance.trace(
            execution,
            actor_id or execution.created_by,
            self.DAG_DECISION_EVENT,
            "planned",
            data={
                "decision_id": decision_id,
                "workflow_version_id": str(getattr(execution, "workflow_version_id", "")),
                "completed_node_ids": completed,
                "frontier_node_ids": frontier,
                "selected_predecessors": selected,
            },
        )

    async def _resolve_dag_context(self, execution, definition: dict, state_data: dict):
        """统一解析首次执行与 Resume 的 DAG frontier，并为多根首次执行初始化独立分支状态。"""
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
                branch_state_data = (
                    {node_id: dict(state_data) for node_id in plan.frontier_node_ids}
                    if len(plan.frontier_node_ids) > 1
                    else {}
                )
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
                resume_plan=plan,
            )
            await self._record_dag_frontier_decision(
                execution,
                definition,
                plan,
                getattr(execution, "created_by", None),
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return runtime_plan, branch_state_data

    async def _execute_node_with_policy(self, service, execution, node: dict, current_data: dict, actor_id,
                                        is_admin: bool, workflow_timeout: int, max_retries: int, started: float,
                                        workflow_retry_counter: list[int]) -> dict:
        """复用基础 Runtime 的 Retry 策略，并在预算或 Workflow deadline 耗尽时补充统一治理事实。

        Args:
            service: Execution 领域服务。
            execution: 当前 Workflow Execution。
            node: 当前节点定义。
            current_data: 节点输入状态。
            actor_id: 当前执行者。
            is_admin: 是否以管理员身份执行。
            workflow_timeout: Workflow 总超时毫秒数。
            max_retries: Workflow 级 Retry 总预算。
            started: Workflow Runtime 开始时间。
            workflow_retry_counter: 当前 Workflow 已消费的 Retry 次数。

        Returns:
            基础 Runtime 执行器返回的节点输出。

        Raises:
            BaseException: 基础 Runtime 判定节点不可继续重试时原样抛出。

        设计意图：Retry 算法仍只有基础 Runtime 一个正式实现；DAG 扩展层只负责补齐“耗尽”治理事实，避免成功调度事件与最终耗尽事件之间出现可观测性断层。
        """
        try:
            return await super()._execute_node_with_policy(
                service,
                execution,
                node,
                current_data,
                actor_id,
                is_admin,
                workflow_timeout,
                max_retries,
                started,
                workflow_retry_counter,
            )
        except HTTPException as exc:
            detail = str(exc.detail)
            if exc.status_code == 504 and detail == "Retry backoff exceeds workflow deadline":
                await service.governance.trace(
                    execution,
                    actor_id,
                    "node.retry.exhausted",
                    "failed",
                    node_id=node["id"],
                    error_code="WORKFLOW_TIMEOUT",
                    data={"reason": "workflow_deadline"},
                )
                await service.governance.audit(
                    execution,
                    actor_id,
                    "workflow.node.retry_exhausted",
                    "failed",
                    error_code="WORKFLOW_TIMEOUT",
                    metadata={"node_id": node["id"], "reason": "workflow_deadline"},
                )
            elif workflow_retry_counter[0] >= max_retries:
                error_code = self.classify_error(exc)
                await service.governance.trace(
                    execution,
                    actor_id,
                    "node.retry.exhausted",
                    "failed",
                    node_id=node["id"],
                    error_code=error_code,
                    data={"reason": "retry_budget"},
                )
                await service.governance.audit(
                    execution,
                    actor_id,
                    "workflow.node.retry_exhausted",
                    "failed",
                    error_code=error_code,
                    metadata={"node_id": node["id"], "reason": "retry_budget"},
                )
            raise
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as exc:
            if workflow_retry_counter[0] >= max_retries:
                error_code = self.classify_error(exc)
                await service.governance.trace(
                    execution,
                    actor_id,
                    "node.retry.exhausted",
                    "failed",
                    node_id=node["id"],
                    error_code=error_code,
                    data={"reason": "retry_budget"},
                )
                await service.governance.audit(
                    execution,
                    actor_id,
                    "workflow.node.retry_exhausted",
                    "failed",
                    error_code=error_code,
                    metadata={"node_id": node["id"], "reason": "retry_budget"},
                )
            raise

    async def execute_node(self, node: dict, input_data: dict, actor_id, is_admin: bool,
                           session_id, tenant_id=None, execution=None) -> dict:
        """执行 Join Node 或委托其它 Node 给基础 Runtime。"""
        if node.get("type") == "join":
            return dict(input_data)
        return await super().execute_node(node, input_data, actor_id, is_admin, session_id, tenant_id, execution=execution)

    async def execute(self, execution, version, actor_id, is_admin: bool = False,
                      allow_legacy_empty_nodes: bool = False) -> dict:
        """执行 Workflow，并在 Recovery Resume 场景延续持久化 trace_id。"""
        # 普通 Execution 没有 Recovery trace lineage，不应执行无意义的 Trace 查询；
        # 这也保证普通 Runtime 的单元测试与实际运行路径不依赖 Recovery 数据源。
        if getattr(execution, "resume_of_execution_id", None) is None:
            return await super().execute(execution, version, actor_id, is_admin, allow_legacy_empty_nodes=allow_legacy_empty_nodes)

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
