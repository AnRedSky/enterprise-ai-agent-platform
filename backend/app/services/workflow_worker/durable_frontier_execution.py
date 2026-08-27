"""Durable Frontier Runtime 异常收敛适配器。

职责：把单个 Durable Frontier 接入现有 WorkflowRuntime 的 Planner / Node 执行能力，并将运行异常统一收敛到 Frontier Retry / Failed 生命周期。
边界：不复制 Runtime、Planner、Checkpoint 或 Retry 算法；只编排一次 Frontier dispatch 及异常状态收敛。
关键依赖：DurableFrontierWorkflowWorker、WorkflowRuntime、WorkflowDagResumePlanner、Frontier Repository、Frontier Retry Policy。
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
from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner
from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_repository import enqueue_frontier, transition_owned_frontier
from app.services.workflow.frontier_retry import FrontierRetryPolicy, schedule_frontier_retry
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
        """将 Runtime 异常分类为 Durable Retry 或终态失败。

        Args:
            exc: Runtime、Provider 或 Planner 执行阶段抛出的异常。

        Returns:
            tuple[bool, str, str]: 是否可重试、稳定错误码、面向持久化记录的错误信息。

        设计约束：仅将明确的临时故障视为可重试；业务 Contract、Planner 不一致和参数错误不能
        通过 Frontier Retry 无限掩盖。HTTP 5xx、429、408、网络连接异常和 Circuit Open 属于
        基础设施临时故障，进入 Frontier retry_wait；其余异常进入 Frontier failed。
        """
        if isinstance(exc, CircuitOpenError):
            return True, "WORKFLOW_CIRCUIT_OPEN", str(exc)
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return True, "WORKFLOW_TRANSIENT_FAILURE", str(exc) or exc.__class__.__name__
        if isinstance(exc, HTTPException):
            if exc.status_code in {408, 429, 500, 502, 503, 504}:
                detail = exc.detail if isinstance(exc.detail, str) else repr(exc.detail)
                return True, f"WORKFLOW_HTTP_{exc.status_code}", detail
            detail = exc.detail if isinstance(exc.detail, str) else repr(exc.detail)
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

    async def _converge_failure(self, frontier: WorkflowFrontier, exc: Exception) -> None:
        """在独立补偿事务中将 Runtime 异常收敛到 retry_wait 或 failed。

        Args:
            frontier: 本次 Claim 的 Durable Frontier 及其 fencing generation。
            exc: 导致本次 Frontier dispatch 失败的异常。

        Returns:
            None。状态变化通过新的 caller-owned 事务提交。

        事务边界：Runtime 原事务发生异常后先回滚未提交事实，再重新锁定同一 Frontier 与
        Execution；Retry / Failed 状态和 Execution ownership 释放在同一补偿事务中提交。
        这样不会把半完成 Node fact 与 Retry 状态拆成两个提交。
        """
        retryable, error_code, error_message = self._classify_failure(exc)
        now = datetime.now(UTC).replace(tzinfo=None)
        async with SessionLocal() as db:
            locked_frontier = (
                await db.execute(
                    select(WorkflowFrontier)
                    .where(
                        WorkflowFrontier.id == frontier.id,
                        WorkflowFrontier.tenant_id == frontier.tenant_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            execution = (
                await db.execute(
                    select(WorkflowExecution)
                    .where(
                        WorkflowExecution.id == frontier.execution_id,
                        WorkflowExecution.tenant_id == frontier.tenant_id,
                    )
                    .with_for_update()
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
                policy = self._retry_policy(version)
                updated_frontier = await schedule_frontier_retry(
                    db,
                    frontier=locked_frontier,
                    worker_owner=self.owner,
                    attempt=frontier.attempt,
                    now=now,
                    error_code=error_code,
                    error_message=error_message,
                    policy=policy,
                )
                if updated_frontier.status == "failed":
                    execution_service = WorkflowExecutionService(db)
                    await execution_service.transition(
                        execution,
                        "failed",
                        error_code=error_code,
                        error_message=error_message,
                        actor_id=execution.created_by,
                    )
                    return
                execution.worker_owner = None
                execution.worker_lease_expires_at = None
                execution.error_code = error_code
                execution.error_message = error_message
                await db.commit()
                return

            await transition_owned_frontier(
                db,
                frontier_id=locked_frontier.id,
                worker_owner=self.owner,
                attempt=frontier.attempt,
                target_status="failed",
                now=now,
            )
            execution_service = WorkflowExecutionService(db)
            await execution_service.transition(
                execution,
                "failed",
                error_code=error_code,
                error_message=error_message,
                actor_id=execution.created_by,
            )

    async def execute_frontier(self, frontier: WorkflowFrontier) -> None:
        """执行一个 Durable Frontier，并在异常时进入统一 Retry / Failed 生命周期。

        Args:
            frontier: 已由当前 Worker Claim 且携带 fencing generation 的 Frontier。

        Returns:
            None。成功结果通过当前事务持久化；失败结果通过 Durable Frontier 异常收敛事务持久化。

        Raises:
            Exception: 异常收敛完成后继续向 dispatch 层传播原始异常，便于 Worker 监控和日志记录。

        事务边界：正常路径由当前 Frontier Runtime 事务负责提交；异常路径先回滚 Runtime 事务，
        再由 _converge_failure 使用独立事务提交 Retry / Failed 状态，避免半完成事实与异常状态拆分。
        """
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

                    if version.definition.get("edges"):
                        plan = WorkflowDagResumePlanner.plan(
                            definition=version.definition,
                            completed_node_ids=completed_ids,
                            state_data_by_node=state_by_node,
                        )
                        # Scheduled Trigger 历史记录曾以完整 nodes 集合作为首个 Frontier。
                        # 首次 dispatch 允许该 bootstrap Frontier 包含 Planner root；从第二个 Frontier 起必须严格一致。
                        if completed_ids and tuple(frontier.node_ids) != plan.frontier_node_ids:
                            raise HTTPException(409, "Durable Frontier 与当前 Planner frontier 不一致")
                        branch_state = runtime._build_frontier_branch_states(
                            version.definition,
                            plan.frontier_node_ids,
                            completed_nodes,
                            plan.selected_predecessor_node_ids,
                        ) if completed_ids else {}
                        if len(plan.frontier_node_ids) > 1:
                            result = await runtime._execute_multi_frontier(
                                service, execution, plan, branch_state, execution.created_by, False,
                                timeout, max_retries, started, retry_counter,
                            )
                            if not result.join_ready:
                                raise HTTPException(409, "DAG Multi-frontier Branch 尚未全部完成")
                            state_data = result.merged_state_data or {}
                        elif plan.frontier_node_ids:
                            node_id = plan.frontier_node_ids[0]
                            state_data = await runtime._execute_node_with_policy(
                                service,
                                execution,
                                node_by_id[node_id],
                                branch_state.get(node_id, dict(execution.input_data or {})),
                                execution.created_by,
                                False,
                                timeout,
                                max_retries,
                                started,
                                retry_counter,
                            )
                        else:
                            state_data = dict(execution.output_data or execution.input_data or {})

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
                        state_data = dict(execution.input_data or {})
                        for node_id in executable_ids:
                            state_data = await runtime._execute_node_with_policy(
                                service, execution, node_by_id[node_id], state_data,
                                execution.created_by, False, timeout, max_retries,
                                started, retry_counter,
                            )
                        completed_after = await runtime._load_completed_resume_nodes(execution)
                        after_ids = {node.node_id for node in completed_after}
                        next_ids = tuple(node_id for node_id in ordered if node_id not in after_ids)[:1]
                        fingerprint = self._bootstrap_fingerprint(execution.id, version.id, ordered)

                    await transition_owned_frontier(
                        db,
                        frontier_id=frontier.id,
                        worker_owner=self.owner,
                        attempt=frontier.attempt,
                        target_status="completed",
                        now=now,
                    )
                    if next_ids:
                        identity = WorkflowFrontierIdentity(
                            execution_id=execution.id,
                            workflow_version_id=version.id,
                            decision_fingerprint=fingerprint,
                            node_ids=tuple(next_ids),
                        )
                        await enqueue_frontier(
                            db,
                            tenant_id=frontier.tenant_id,
                            identity=identity,
                            node_ids=identity.node_ids,
                            now=now,
                        )
                        await db.commit()
                    else:
                        await service.transition(
                            execution,
                            "completed",
                            output_data=state_data,
                            actor_id=execution.created_by,
                        )
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
