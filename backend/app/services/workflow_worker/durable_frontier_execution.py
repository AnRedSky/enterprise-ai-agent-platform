"""Durable Frontier Runtime 推进适配器。

职责：把单个 Durable Frontier 接入现有 WorkflowRuntime 的 Planner / Node 执行能力，并在当前外层事务中完成 Frontier 后继推进。
边界：不复制 Runtime、Planner、Checkpoint 或 Retry 算法；仅负责 Frontier Worker 的一次 durable dispatch 编排。
关键依赖：DurableFrontierWorkflowWorker、WorkflowRuntime、WorkflowDagResumePlanner、Frontier progression。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.models.workflow import WorkflowVersion
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.runtime.workflow import WorkflowRuntime
from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner
from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_repository import enqueue_frontier, transition_owned_frontier
from app.services.workflow_worker.frontier_runtime import DurableFrontierWorkflowWorker


@dataclass(frozen=True)
class DurableFrontierExecutionResult:
    """一次 Frontier 执行后的确定性推进结果。"""

    state_data: dict
    decision_fingerprint: str
    next_node_ids: tuple[str, ...]


class PlannerDrivenDurableFrontierWorkflowWorker(DurableFrontierWorkflowWorker):
    """以 Planner 输出作为单次 Frontier 执行边界，并复用唯一 WorkflowRuntime。"""

    async def _load_execution_version(self, frontier: WorkflowFrontier) -> tuple[WorkflowExecution, WorkflowVersion]:
        """读取 Frontier 对应 Execution 与冻结的 Workflow Version，并强制 tenant scope。

        Args:
            frontier: 已完成 claim 且处于当前 Worker ownership 下的 Frontier。

        Returns:
            `(execution, version)`，用于本次 Frontier Runtime 执行。

        Raises:
            HTTPException: Execution 或 Workflow Version 不存在或租户不一致。
        """
        async with self._db_session() as db:
            execution = (
                await db.execute(
                    select(WorkflowExecution).where(
                        WorkflowExecution.id == frontier.execution_id,
                        WorkflowExecution.tenant_id == frontier.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if execution is None:
                raise HTTPException(404, "Workflow Execution 不存在")
            version = (
                await db.execute(
                    select(WorkflowVersion).where(
                        WorkflowVersion.id == frontier.workflow_version_id,
                    )
                )
            ).scalar_one_or_none()
            if version is None:
                raise HTTPException(409, "Workflow Version 不存在")
            return execution, version

    @staticmethod
    def _bootstrap_fingerprint(execution_id: UUID, version_id: UUID, node_ids: tuple[str, ...]) -> str:
        """为无 DAG Edge 的顺序 Workflow 生成稳定的首批 frontier decision fingerprint。"""
        payload = "|".join((str(execution_id), str(version_id), ",".join(node_ids))).encode("utf-8")
        return sha256(payload).hexdigest()

    async def _execute_one_frontier(self, frontier: WorkflowFrontier) -> DurableFrontierExecutionResult:
        """执行当前 Frontier 对应的一批 Node，并让 Planner 计算后继 Frontier。

        Args:
            frontier: 已取得 Worker ownership 的 Durable Frontier。

        Returns:
            当前 Frontier 执行后的状态、后继 decision fingerprint 与后继 Node 集合。

        Raises:
            HTTPException: Planner、Runtime 或 Node 执行无法继续时抛出领域错误。

        设计意图：一次 Worker dispatch 只消费一个 durable frontier。Runtime 原有“连续执行完整 DAG”入口仍保留给 HTTP / 兼容调用；Durable Worker 通过已有 Runtime 内部执行契约只推进当前 Planner frontier，避免 Scheduler 与 Runtime 同时消费同一 work item。
        """
        async with self._db_session() as db:
            execution = (
                await db.execute(
                    select(WorkflowExecution).where(
                        WorkflowExecution.id == frontier.execution_id,
                        WorkflowExecution.tenant_id == frontier.tenant_id,
                    ).with_for_update()
                )
            ).scalar_one_or_none()
            if execution is None:
                raise HTTPException(404, "Workflow Execution 不存在")
            version = (
                await db.execute(
                    select(WorkflowVersion).where(WorkflowVersion.id == frontier.workflow_version_id)
                )
            ).scalar_one_or_none()
            if version is None:
                raise HTTPException(409, "Workflow Version 不存在")
            runtime = WorkflowRuntime(db)
            nodes = runtime.validate_definition(version.definition)
            node_by_id = {node["id"]: node for node in nodes}
            completed_nodes = await runtime._load_completed_resume_nodes(execution)
            completed_ids = {node.node_id for node in completed_nodes}
            state_by_node = {node.node_id: dict(node.output_data or {}) for node in completed_nodes}
            plan = WorkflowDagResumePlanner.plan(
                definition=version.definition,
                completed_node_ids=completed_ids,
                state_data_by_node=state_by_node,
            ) if version.definition.get("edges") else None
            if plan is None:
                ordered = tuple(node["id"] for node in nodes)
                remaining = tuple(node_id for node_id in ordered if node_id not in completed_ids)
                if not remaining:
                    return DurableFrontierExecutionResult(dict(execution.output_data or {}), self._bootstrap_fingerprint(execution.id, version.id, ordered), ())
                current_ids = tuple(frontier.node_ids)
                executable_ids = tuple(node_id for node_id in current_ids if node_id in node_by_id and node_id not in completed_ids)
                if not executable_ids:
                    executable_ids = (remaining[0],)
                current_data = dict(execution.input_data or {})
                retry_counter = [0]
                import time
                started = time.monotonic()
                config = version.definition.get("config") or {}
                timeout = runtime.resolve_timeout_ms(config)
                budget = config.get("retry_budget") or {}
                max_retries = int(budget.get("max_retries", 0))
                for node_id in executable_ids:
                    current_data = await runtime._execute_node_with_policy(
                        runtime.execution_service or __import__("app.services.workflow", fromlist=["WorkflowExecutionService"]).WorkflowExecutionService(db),
                        execution,
                        node_by_id[node_id],
                        current_data,
                        execution.created_by,
                        False,
                        timeout,
                        max_retries,
                        started,
                        retry_counter,
                    )
                next_ids = tuple(node_id for node_id in ordered if node_id not in completed_ids and node_id not in executable_ids)
                return DurableFrontierExecutionResult(current_data, self._bootstrap_fingerprint(execution.id, version.id, ordered), next_ids[:1])

            if tuple(frontier.node_ids) != plan.frontier_node_ids:
                raise HTTPException(409, "Durable Frontier 与当前 Planner frontier 不一致")
            current_data = dict(execution.input_data or {})
            retry_counter = [0]
            import time
            started = time.monotonic()
            config = version.definition.get("config") or {}
            timeout = runtime.resolve_timeout_ms(config)
            budget = config.get("retry_budget") or {}
            max_retries = int(budget.get("max_retries", 0))
            service = runtime.execution_service or __import__("app.services.workflow", fromlist=["WorkflowExecutionService"]).WorkflowExecutionService(db)
            branch_state = runtime._build_frontier_branch_states(version.definition, plan.frontier_node_ids, completed_nodes, plan.selected_predecessor_node_ids) if completed_ids else {}
            if len(plan.frontier_node_ids) > 1:
                result = await runtime._execute_multi_frontier(service, execution, plan, branch_state, execution.created_by, False, timeout, max_retries, started, retry_counter)
                if not result.join_ready:
                    raise HTTPException(409, "DAG Multi-frontier Branch 尚未全部完成")
                current_data = result.merged_state_data or {}
            else:
                node_id = plan.frontier_node_ids[0]
                current_data = await runtime._execute_node_with_policy(
                    service,
                    execution,
                    node_by_id[node_id],
                    branch_state.get(node_id, current_data),
                    execution.created_by,
                    False,
                    timeout,
                    max_retries,
                    started,
                    retry_counter,
                )
            completed_nodes_after = await runtime._load_completed_resume_nodes(execution)
            completed_after = {node.node_id for node in completed_nodes_after}
            state_after = {node.node_id: dict(node.output_data or {}) for node in completed_nodes_after}
            next_plan = WorkflowDagResumePlanner.plan(
                definition=version.definition,
                completed_node_ids=completed_after,
                state_data_by_node=state_after,
            )
            return DurableFrontierExecutionResult(current_data, next_plan.decision_fingerprint, next_plan.frontier_node_ids)

    async def execute_frontier(self, frontier: WorkflowFrontier) -> None:
        """在单个 Frontier 外层事务中完成 Node facts、Frontier terminal state 与后继 Frontier。

        Args:
            frontier: 已 Claim 且持有当前 Worker fencing generation 的 Frontier。

        事务边界：Node Checkpoint、当前 Frontier terminal transition、Next Frontier enqueue 以及最终 Execution terminal transition 必须在同一外层事务中提交。
        """
        from app.infrastructure.db import SessionLocal
        from app.services.workflow import WorkflowExecutionService

        heartbeat = asyncio.create_task(self._renew_frontier_forever(frontier.id, frontier.attempt))
        try:
            async with SessionLocal() as db:
                execution = (
                    await db.execute(
                        select(WorkflowExecution).where(
                            WorkflowExecution.id == frontier.execution_id,
                            WorkflowExecution.tenant_id == frontier.tenant_id,
                        ).with_for_update()
                    )
                ).scalar_one_or_none()
                if execution is None:
                    await db.rollback()
                    return
                version = (
                    await db.execute(select(WorkflowVersion).where(WorkflowVersion.id == frontier.workflow_version_id))
                ).scalar_one_or_none()
                if version is None:
                    await db.rollback()
                    return
                runtime = WorkflowRuntime(db)
                service = WorkflowExecutionService(db)
                nodes = runtime.validate_definition(version.definition)
                node_by_id = {node["id"]: node for node in nodes}
                completed_nodes = await runtime._load_completed_resume_nodes(execution)
                completed_ids = {node.node_id for node in completed_nodes}
                state_by_node = {node.node_id: dict(node.output_data or {}) for node in completed_nodes}
                if version.definition.get("edges"):
                    plan = WorkflowDagResumePlanner.plan(definition=version.definition, completed_node_ids=completed_ids, state_data_by_node=state_by_node)
                    if tuple(frontier.node_ids) != plan.frontier_node_ids:
                        raise HTTPException(409, "Durable Frontier 与当前 Planner frontier 不一致")
                    branch_state = runtime._build_frontier_branch_states(version.definition, plan.frontier_node_ids, completed_nodes, plan.selected_predecessor_node_ids) if completed_ids else {}
                    retry_counter = [0]
                    import time
                    started = time.monotonic()
                    config = version.definition.get("config") or {}
                    timeout = runtime.resolve_timeout_ms(config)
                    budget = config.get("retry_budget") or {}
                    max_retries = int(budget.get("max_retries", 0))
                    if len(plan.frontier_node_ids) > 1:
                        result = await runtime._execute_multi_frontier(service, execution, plan, branch_state, execution.created_by, False, timeout, max_retries, started, retry_counter)
                        if not result.join_ready:
                            raise HTTPException(409, "DAG Multi-frontier Branch 尚未全部完成")
                        state_data = result.merged_state_data or {}
                    else:
                        node = node_by_id[plan.frontier_node_ids[0]]
                        state_data = await runtime._execute_node_with_policy(service, execution, node, branch_state.get(node["id"], dict(execution.input_data or {})), execution.created_by, False, timeout, max_retries, started, retry_counter)
                    completed_after = await runtime._load_completed_resume_nodes(execution)
                    after_ids = {node.node_id for node in completed_after}
                    after_state = {node.node_id: dict(node.output_data or {}) for node in completed_after}
                    next_plan = WorkflowDagResumePlanner.plan(definition=version.definition, completed_node_ids=after_ids, state_data_by_node=after_state)
                    next_ids = next_plan.frontier_node_ids
                    fingerprint = next_plan.decision_fingerprint
                else:
                    ordered = tuple(node["id"] for node in nodes)
                    current_ids = tuple(frontier.node_ids)
                    executable_ids = tuple(node_id for node_id in current_ids if node_id in node_by_id and node_id not in completed_ids)
                    if not executable_ids:
                        remaining = tuple(node_id for node_id in ordered if node_id not in completed_ids)
                        executable_ids = remaining[:1]
                    retry_counter = [0]
                    import time
                    started = time.monotonic()
                    config = version.definition.get("config") or {}
                    timeout = runtime.resolve_timeout_ms(config)
                    budget = config.get("retry_budget") or {}
                    max_retries = int(budget.get("max_retries", 0))
                    state_data = dict(execution.input_data or {})
                    for node_id in executable_ids:
                        state_data = await runtime._execute_node_with_policy(service, execution, node_by_id[node_id], state_data, execution.created_by, False, timeout, max_retries, started, retry_counter)
                    completed_after = await runtime._load_completed_resume_nodes(execution)
                    after_ids = {node.node_id for node in completed_after}
                    next_ids = tuple(node_id for node_id in ordered if node_id not in after_ids)[:1]
                    fingerprint = self._bootstrap_fingerprint(execution.id, version.id, tuple(ordered))

                await transition_owned_frontier(db, frontier_id=frontier.id, worker_owner=self.owner, attempt=frontier.attempt, target_status="completed", now=datetime.now(UTC).replace(tzinfo=None))
                if next_ids:
                    identity = WorkflowFrontierIdentity(execution_id=execution.id, workflow_version_id=version.id, decision_fingerprint=fingerprint, node_ids=tuple(next_ids))
                    await enqueue_frontier(db, tenant_id=frontier.tenant_id, identity=identity, node_ids=identity.node_ids, now=datetime.now(UTC).replace(tzinfo=None))
                else:
                    await service.transition(execution, "completed", output_data=state_data, actor_id=execution.created_by)
                await db.commit()
        except Exception:
            try:
                await db.rollback()
            except Exception:
                pass
            raise
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except asyncio.CancelledError:
                pass
