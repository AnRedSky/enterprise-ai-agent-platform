"""Durable Frontier Runtime 异常收敛适配器。

职责：把单个 Durable Frontier 接入现有 WorkflowRuntime 的 Planner / Node 执行能力，并将运行异常统一收敛到 Frontier Retry / Failed 生命周期。
边界：不复制 Runtime、Planner、Checkpoint 或 Retry 算法；只编排一次 Frontier dispatch 及异常状态收敛。
关键依赖：DurableFrontierWorkflowWorker、WorkflowRuntime、WorkflowDagResumePlanner、WorkflowDagMultiFrontierExecutor、Frontier Repository、Frontier Progression、Frontier Retry Policy。
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow import WorkflowVersion
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.runtime.workflow import CircuitOpenError, WorkflowRuntime
from app.services.workflow import WorkflowExecutionService
from app.services.workflow.checkpoint.recovery.dag_executor import WorkflowDagMultiFrontierExecutor
from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner
from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_progression import complete_frontier_with_checkpoint
from app.services.workflow.frontier_repository import transition_owned_frontier
from app.services.workflow.frontier_retry import FrontierRetryPolicy, schedule_frontier_retry
from app.services.workflow.governance import WorkflowGovernanceService
from app.services.workflow_worker.frontier_runtime import DurableFrontierWorkflowWorker


class PlannerDrivenDurableFrontierWorkflowWorker(DurableFrontierWorkflowWorker):
    """以 Planner 输出作为单次 Frontier 执行边界，并统一收敛 Runtime 异常。"""

    @staticmethod
    def _bootstrap_fingerprint(execution_id, version_id, node_ids: tuple[str, ...]) -> str:
        """为无 DAG Edge 的顺序 Workflow 生成稳定 decision fingerprint。"""
        payload = "|".join((str(execution_id), str(version_id), ",".join(node_ids))).encode("utf-8")
        return sha256(payload).hexdigest()

    @staticmethod
    def _classify_failure(exc: Exception) -> tuple[bool, str, str]:
        """将 Runtime 异常分类为 Durable Retry 或终态失败。"""
        if isinstance(exc, CircuitOpenError):
            return True, "WORKFLOW_CIRCUIT_OPEN", str(exc)
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return True, "WORKFLOW_TRANSIENT_FAILURE", str(exc) or exc.__class__.__name__
        if isinstance(exc, HTTPException):
            detail = exc.detail if isinstance(exc.detail, str) else repr(exc.detail)
            if exc.status_code in {408, 429, 500, 502, 503, 504}:
                return True, f"WORKFLOW_HTTP_{exc.status_code}", detail
            return False, f"WORKFLOW_HTTP_{exc.status_code}", detail
        return False, "WORKFLOW_EXECUTION_FAILED", str(exc) or exc.__class__.__name__

    @staticmethod
    def _retry_policy(version: WorkflowVersion) -> FrontierRetryPolicy:
        """从 Workflow Version 的 retry_budget 构造 Frontier Retry Policy。"""
        config = version.definition.get("config") or {}
        retry_budget = config.get("retry_budget") or {}
        max_retries = max(0, int(retry_budget.get("max_retries", 0)))
        return FrontierRetryPolicy(
            max_attempts=max(1, max_retries + 1),
            base_delay_seconds=float(retry_budget.get("base_delay_seconds", 1.0)),
            max_delay_seconds=float(retry_budget.get("max_delay_seconds", 300.0)),
        )

    async def _execute_multi_frontier_without_checkpoint(
        self,
        runtime: WorkflowRuntime,
        service,
        execution,
        plan,
        branch_state_data,
        actor_id,
        is_admin,
        workflow_timeout,
        max_retries,
        started,
        workflow_retry_counter,
    ):
        """执行 Multi-frontier，但把 Checkpoint 持久化交给 Durable Frontier progression。

        Args:
            runtime: 唯一 WorkflowRuntime 实例，提供 Node 执行与 Retry 策略。
            service: 当前 Execution Service。
            execution: 当前 Workflow Execution。
            plan: 已确定的 DAG frontier plan。
            branch_state_data: Planner 计算出的各 Branch 输入状态。
            actor_id: 当前执行操作者。
            is_admin: 是否使用管理员执行权限。
            workflow_timeout: Workflow 总超时时间，单位毫秒。
            max_retries: Workflow Retry budget。
            started: Runtime 开始时间。
            workflow_retry_counter: 当前 Runtime 已消耗的 Retry 次数。

        Returns:
            Multi-frontier Executor 结果。Branch NodeExecution 仍写入当前事务，
            但不提前追加 `frontier_completed` Checkpoint；外层 progression 会把 Frontier、
            Checkpoint、Execution terminalization 与 Next Frontier 一次性提交，避免同一 frontier 产生两个完成快照。
        """
        async def execute_branch(node, input_data):
            return await runtime._execute_node_with_policy(
                service,
                execution,
                node,
                input_data,
                actor_id,
                is_admin,
                workflow_timeout,
                max_retries,
                started,
                workflow_retry_counter,
            )

        async def checkpoint_branch(node_id, output):
            if not isinstance(output, dict):
                raise ValueError(f"DAG frontier Node {node_id} Checkpoint state 必须为对象")

        return await WorkflowDagMultiFrontierExecutor.execute(
            plan,
            branch_state_data=branch_state_data,
            executor=execute_branch,
            checkpoint_writer=checkpoint_branch,
        )

    async def _mark_execution_failed_in_transaction(
        self,
        db,
        execution: WorkflowExecution,
        *,
        now: datetime,
        error_code: str,
        error_message: str,
    ) -> None:
        """在当前 Frontier failure 事务内 terminalize Execution，不调用会自行 commit 的通用 transition。

        Frontier failure 与 Execution failure 必须保持同一 COMMIT/ROLLBACK 边界；否则通用
        WorkflowExecutionService.transition() 的内部 commit 会先提交 Execution，再让 Frontier
        retry/failed 状态单独提交，产生半完成 durable lifecycle。
        """
        if execution.status in {"completed", "failed", "cancelled"}:
            if execution.status != "failed":
                raise HTTPException(409, f"Execution 已进入终态 {execution.status}，拒绝重复 failure")
            return
        if execution.status not in {"pending", "running"}:
            raise HTTPException(409, f"Execution 当前状态 {execution.status} 不允许 failure terminalization")
        current = execution.status
        execution.status = "failed"
        execution.ended_at = now
        execution.current_node_id = None
        execution.error_code = error_code
        execution.error_message = error_message
        execution.worker_owner = None
        execution.worker_lease_expires_at = None
        actor_id = execution.created_by
        governance = WorkflowGovernanceService(db)
        await governance.trace(
            execution,
            actor_id,
            "execution.state_changed",
            "failed",
            error_code=error_code,
            error_message=error_message,
            data={"from": current, "to": "failed", "frontier_id": str(execution.id)},
        )
        await governance.audit(
            execution,
            actor_id,
            "workflow.execution.failed",
            "failed",
            error_code=error_code,
        )

    async def _converge_failure(self, frontier: WorkflowFrontier, exc: Exception) -> None:
        """在单一补偿事务中将 Runtime 异常收敛到 retry_wait 或 failed。"""
        retryable, error_code, error_message = self._classify_failure(exc)
        now = datetime.now(UTC).replace(tzinfo=None)
        async with SessionLocal() as db:
            locked_frontier = (
                await db.execute(
                    select(WorkflowFrontier).where(
                        WorkflowFrontier.id == frontier.id,
                        WorkflowFrontier.tenant_id == frontier.tenant_id,
                    ).with_for_update()
                )
            ).scalar_one_or_none()
            execution = (
                await db.execute(
                    select(WorkflowExecution).where(
                        WorkflowExecution.id == frontier.execution_id,
                        WorkflowExecution.tenant_id == frontier.tenant_id,
                    ).with_for_update()
                )
            ).scalar_one_or_none()
            if locked_frontier is None or execution is None:
                await db.rollback()
                return
            if retryable:
                version = (
                    await db.execute(
                        select(WorkflowVersion).where(WorkflowVersion.id == frontier.workflow_version_id)
                    )
                ).scalar_one_or_none()
                if version is None:
                    await db.rollback()
                    return
                updated_frontier = await schedule_frontier_retry(
                    db, frontier=locked_frontier, worker_owner=self.owner, attempt=frontier.attempt,
                    now=now, error_code=error_code, error_message=error_message,
                    policy=self._retry_policy(version),
                )
                if updated_frontier.status == "failed":
                    await self._mark_execution_failed_in_transaction(
                        db, execution, now=now, error_code=error_code, error_message=error_message,
                    )
                else:
                    execution.worker_owner = None
                    execution.worker_lease_expires_at = None
                    execution.error_code = error_code
                    execution.error_message = error_message
                await db.commit()
                return
            await transition_owned_frontier(
                db, frontier_id=locked_frontier.id, worker_owner=self.owner,
                attempt=frontier.attempt, target_status="failed", now=now,
            )
            await self._mark_execution_failed_in_transaction(
                db, execution, now=now, error_code=error_code, error_message=error_message,
            )
            await db.commit()

    async def execute_frontier(self, frontier: WorkflowFrontier) -> None:
        """执行一个 Durable Frontier，并通过统一 Progression primitive 完成成功提交。"""
        heartbeat = asyncio.create_task(self._renew_frontier_forever(frontier.id, frontier.attempt))
        try:
            async with SessionLocal() as db:
                try:
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
                        await db.execute(
                            select(WorkflowVersion).where(WorkflowVersion.id == frontier.workflow_version_id)
                        )
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
                    config = version.definition.get("config") or {}
                    timeout = runtime.resolve_timeout_ms(config)
                    retry_budget = config.get("retry_budget") or {}
                    max_retries = int(retry_budget.get("max_retries", 0))
                    retry_counter = [0]
                    started = time.monotonic()
                    now = datetime.now(UTC).replace(tzinfo=None)
                    checkpoint_state: dict = dict(execution.input_data or {})

                    if version.definition.get("edges"):
                        plan = WorkflowDagResumePlanner.plan(
                            definition=version.definition,
                            completed_node_ids=completed_ids,
                            state_data_by_node=state_by_node,
                        )
                        if completed_ids and tuple(frontier.node_ids) != plan.frontier_node_ids:
                            raise HTTPException(409, "Durable Frontier 与当前 Planner frontier 不一致")
                        branch_state = runtime._build_frontier_branch_states(
                            version.definition, plan.frontier_node_ids, completed_nodes,
                            plan.selected_predecessor_node_ids,
                        ) if completed_ids else {}
                        if len(plan.frontier_node_ids) > 1:
                            result = await self._execute_multi_frontier_without_checkpoint(
                                runtime, service, execution, plan, branch_state, execution.created_by, False,
                                timeout, max_retries, started, retry_counter,
                            )
                            if not result.join_ready:
                                raise HTTPException(409, "DAG Multi-frontier Branch 尚未全部完成")
                            checkpoint_state = result.merged_state_data or {}
                        elif plan.frontier_node_ids:
                            checkpoint_node_id = plan.frontier_node_ids[0]
                            checkpoint_state = await runtime._execute_node_with_policy(
                                service, execution, node_by_id[checkpoint_node_id],
                                branch_state.get(checkpoint_node_id, dict(execution.input_data or {})),
                                execution.created_by, False, timeout, max_retries,
                                started, retry_counter,
                            )
                        else:
                            checkpoint_state = dict(execution.output_data or execution.input_data or {})
                        completed_after = await runtime._load_completed_resume_nodes(execution)
                        after_ids = {node.node_id for node in completed_after}
                        after_state = {node.node_id: dict(node.output_data or {}) for node in completed_after}
                        next_plan = WorkflowDagResumePlanner.plan(
                            definition=version.definition,
                            completed_node_ids=after_ids,
                            state_data_by_node=after_state,
                        )
                        next_ids = next_plan.frontier_node_ids
                        fingerprint = next_plan.decision_fingerprint
                    else:
                        ordered = tuple(node["id"] for node in nodes)
                        executable_ids = tuple(
                            node_id for node_id in frontier.node_ids
                            if node_id in node_by_id and node_id not in completed_ids
                        )
                        if not executable_ids:
                            remaining = tuple(node_id for node_id in ordered if node_id not in completed_ids)
                            executable_ids = remaining[:1]
                        checkpoint_state = dict(execution.input_data or {})
                        for node_id in executable_ids:
                            checkpoint_state = await runtime._execute_node_with_policy(
                                service, execution, node_by_id[node_id], checkpoint_state,
                                execution.created_by, False, timeout, max_retries,
                                started, retry_counter,
                            )
                        completed_after = await runtime._load_completed_resume_nodes(execution)
                        after_ids = {node.node_id for node in completed_after}
                        next_ids = tuple(node_id for node in ordered if node_id not in after_ids)[:1]
                        fingerprint = self._bootstrap_fingerprint(execution.id, version.id, ordered)

                    next_identity = None
                    if next_ids:
                        next_identity = WorkflowFrontierIdentity(
                            execution_id=execution.id, workflow_version_id=version.id,
                            decision_fingerprint=fingerprint, node_ids=tuple(next_ids),
                        )
                    await complete_frontier_with_checkpoint(
                        db, frontier=frontier, worker_owner=self.owner, attempt=frontier.attempt,
                        checkpoint_state=checkpoint_state, checkpoint_reason="frontier_completed",
                        next_identity=next_identity, now=now, actor_id=execution.created_by,
                    )
                    await db.commit()
                except Exception:
                    await db.rollback()
                    raise
        except Exception as exc:
            try:
                await self._converge_failure(frontier, exc)
            finally:
                heartbeat.cancel()
                try:
                    await heartbeat
                except asyncio.CancelledError:
                    pass
            raise
        finally:
            if not heartbeat.done():
                heartbeat.cancel()
                try:
                    await heartbeat
                except asyncio.CancelledError:
                    pass
