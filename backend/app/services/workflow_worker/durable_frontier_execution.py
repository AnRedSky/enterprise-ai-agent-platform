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
from sqlalchemy import select, update

from app.infrastructure.db import SessionLocal
from app.models.workflow import WorkflowVersion
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier, WorkflowNodeExecution
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
        self, runtime: WorkflowRuntime, service, execution, plan, branch_state_data,
        actor_id, is_admin, workflow_timeout, max_retries, started, workflow_retry_counter,
    ):
        """执行 Multi-frontier，但把 Checkpoint 持久化交给 Durable Frontier progression。"""
        async def execute_branch(node, input_data):
            return await runtime._execute_node_with_policy(
                service, execution, node, input_data, actor_id, is_admin,
                workflow_timeout, max_retries, started, workflow_retry_counter,
            )

        async def checkpoint_branch(node_id, output):
            if not isinstance(output, dict):
                raise ValueError(f"DAG frontier Node {node_id} Checkpoint state 必须为对象")

        return await WorkflowDagMultiFrontierExecutor.execute(
            plan, branch_state_data=branch_state_data,
            executor=execute_branch, checkpoint_writer=checkpoint_branch,
        )

    async def _mark_active_sibling_frontiers_failed(
        self, db, execution: WorkflowExecution, *, now: datetime,
        error_code: str, error_message: str,
    ) -> None:
        """Execution 进入 failed 时，同事务关闭仍可消费的 sibling Frontier。"""
        await db.execute(
            update(WorkflowFrontier)
            .where(
                WorkflowFrontier.tenant_id == execution.tenant_id,
                WorkflowFrontier.execution_id == execution.id,
                WorkflowFrontier.status.in_(("pending", "retry_wait", "claimed", "running")),
            )
            .values(
                status="failed", completed_at=now, worker_owner=None,
                worker_lease_expires_at=None, error_code=error_code,
                error_message=error_message,
            )
        )

    async def _persist_failed_node_fact(
        self, db, execution: WorkflowExecution, frontier: WorkflowFrontier, *,
        now: datetime, error_code: str, error_message: str,
    ) -> None:
        """在 Frontier 失败补偿事务中恢复本次失败 Node 的 Durable Fact。

        Frontier Runtime 的 Node 状态与 Frontier completion 共用一个事务；Runtime 异常会先回滚该事务，
        若补偿阶段只记录 Frontier/Execution 失败，NodeExecution 的失败事实也会随之丢失，导致 Resume
        无法识别失败 frontier。单 Node Frontier 可确定唯一失败 Node；Multi-frontier 异常不猜测具体分支，
        保留由后续 Frontier/Execution fact 收敛，避免把未执行 sibling 错误标记为 failed。
        """
        node_ids = tuple(str(node_id) for node_id in (frontier.node_ids or []) if node_id)
        if len(node_ids) != 1:
            return
        node_id = node_ids[0]
        result = await db.execute(
            select(WorkflowNodeExecution).where(
                WorkflowNodeExecution.execution_id == execution.id,
                WorkflowNodeExecution.tenant_id == execution.tenant_id,
                WorkflowNodeExecution.node_id == node_id,
            ).with_for_update()
        )
        node = result.scalar_one_or_none()
        if node is None:
            node = WorkflowNodeExecution(
                tenant_id=execution.tenant_id,
                execution_id=execution.id,
                node_id=node_id,
                status="failed",
                attempt=1,
                ended_at=now,
                error_code=error_code,
                error_message=error_message,
            )
            db.add(node)
            return
        if node.status in {"completed", "skipped"}:
            return
        node.status = "failed"
        node.ended_at = now
        node.error_code = error_code
        node.error_message = error_message

    async def _mark_execution_failed_in_transaction(
        self, db, execution: WorkflowExecution, *, now: datetime,
        error_code: str, error_message: str, frontier: WorkflowFrontier | None = None,
    ) -> None:
        """在当前 Frontier failure 事务内 terminalize Execution，并关闭其活动 sibling Frontier。"""
        if execution.status in {"completed", "failed", "cancelled"}:
            if execution.status != "failed":
                raise HTTPException(409, f"Execution 已进入终态 {execution.status}，拒绝重复 failure")
            await self._mark_active_sibling_frontiers_failed(
                db, execution, now=now, error_code=error_code, error_message=error_message,
            )
            return
        if execution.status not in {"pending", "running"}:
            raise HTTPException(409, f"Execution 当前状态 {execution.status} 不允许 failure terminalization")
        if frontier is not None:
            await self._persist_failed_node_fact(
                db, execution, frontier, now=now,
                error_code=error_code, error_message=error_message,
            )
        current = execution.status
        execution.status = "failed"
        execution.ended_at = now
        execution.current_node_id = None
        execution.error_code = error_code
        execution.error_message = error_message
        execution.worker_owner = None
        execution.worker_lease_expires_at = None
        await self._mark_active_sibling_frontiers_failed(
            db, execution, now=now, error_code=error_code, error_message=error_message,
        )
        actor_id = execution.created_by
        governance = WorkflowGovernanceService(db)
        await governance.trace(
            execution, actor_id, "execution.state_changed", "failed",
            error_code=error_code, error_message=error_message,
            data={"from": current, "to": "failed", "frontier_id": str(execution.id)},
        )
        await governance.audit(
            execution, actor_id, "workflow.execution.failed", "failed", error_code=error_code,
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
            if (
                execution.worker_owner != self.owner
                or execution.worker_lease_expires_at is None
                or execution.worker_lease_expires_at <= now
            ):
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
                        db, execution, now=now, error_code=error_code,
                        error_message=error_message, frontier=locked_frontier,
                    )
                else:
                    await self._persist_failed_node_fact(
                        db, execution, locked_frontier, now=now,
                        error_code=error_code, error_message=error_message,
                    )
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
                db, execution, now=now, error_code=error_code,
                error_message=error_message, frontier=locked_frontier,
            )
            await db.commit()

    async def _verify_frontier_consumption_ownership(self, frontier: WorkflowFrontier) -> bool:
        """在真正进入 Runtime 前重新证明 Frontier 与 Execution 仍属于当前 Worker。

        Args:
            frontier: Claim 阶段取得的 Durable Frontier。

        Returns:
            ownership、attempt、状态与两层 lease 均有效时返回 True，否则返回 False。
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        async with SessionLocal() as db:
            frontier_result = await db.execute(
                select(WorkflowFrontier).where(
                    WorkflowFrontier.id == frontier.id,
                    WorkflowFrontier.tenant_id == frontier.tenant_id,
                    WorkflowFrontier.worker_owner == self.owner,
                    WorkflowFrontier.attempt == frontier.attempt,
                    WorkflowFrontier.status == "running",
                    WorkflowFrontier.worker_lease_expires_at.is_not(None),
                    WorkflowFrontier.worker_lease_expires_at > now,
                ).with_for_update()
            )
            locked_frontier = frontier_result.scalar_one_or_none()
            if locked_frontier is None:
                await db.rollback()
                return False
            execution_result = await db.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.id == locked_frontier.execution_id,
                    WorkflowExecution.tenant_id == locked_frontier.tenant_id,
                    WorkflowExecution.worker_owner == self.owner,
                    WorkflowExecution.status.in_(("pending", "running")),
                    WorkflowExecution.worker_lease_expires_at.is_not(None),
                    WorkflowExecution.worker_lease_expires_at > now,
                ).with_for_update()
            )
            execution = execution_result.scalar_one_or_none()
            if execution is None:
                await db.rollback()
                return False
            await db.rollback()
            return True

    async def execute_frontier(self, frontier: WorkflowFrontier) -> None:
        """执行一个 Durable Frontier，并通过统一 Progression primitive 完成成功提交。"""
        if not await self._verify_frontier_consumption_ownership(frontier):
            return
        runtime_task = asyncio.current_task()
        heartbeat = asyncio.create_task(self._renew_frontier_forever(frontier.id, frontier.attempt, runtime_task))
        try:
            async with SessionLocal() as db:
                try:
                    execution = (
                        await db.execute(
                            select(WorkflowExecution).where(
                                WorkflowExecution.id == frontier.execution_id,
                                WorkflowExecution.tenant_id == frontier.tenant_id,
                            )
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
                                execution.created_by, False, timeout, max_retries, started, retry_counter,
                            )
                        completed_after = await runtime._load_completed_resume_nodes(execution)
                        after_ids = {node.node_id for node in completed_after}
                        next_ids = tuple(node_id for node_id in ordered if node_id not in after_ids)[:1]
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
        except asyncio.CancelledError:
            await self._cancel_heartbeat(heartbeat)
            raise
        except Exception as exc:
            try:
                await self._converge_failure(frontier, exc)
            finally:
                await self._cancel_heartbeat(heartbeat)
            raise
        finally:
            if not heartbeat.done():
                await self._cancel_heartbeat(heartbeat)

    @staticmethod
    async def _cancel_heartbeat(heartbeat: asyncio.Task[object]) -> None:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
