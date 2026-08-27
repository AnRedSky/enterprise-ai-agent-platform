"""Durable Frontier Runtime 推进适配器。

职责：把单个 Durable Frontier 接入现有 WorkflowRuntime 的 Planner / Node 执行能力，并在当前事务中完成 Frontier 后继推进。
边界：不复制 Runtime、Planner、Checkpoint 或 Retry 算法；只编排一次 Frontier dispatch。
关键依赖：DurableFrontierWorkflowWorker、WorkflowRuntime、WorkflowDagResumePlanner、Frontier Repository。
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
from app.runtime.workflow import WorkflowRuntime
from app.services.workflow import WorkflowExecutionService
from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner
from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_repository import enqueue_frontier, transition_owned_frontier
from app.services.workflow_worker.frontier_runtime import DurableFrontierWorkflowWorker


class PlannerDrivenDurableFrontierWorkflowWorker(DurableFrontierWorkflowWorker):
    """以 Planner 输出作为单次 Frontier 执行边界，并复用唯一 WorkflowRuntime。"""

    @staticmethod
    def _bootstrap_fingerprint(execution_id, version_id, node_ids: tuple[str, ...]) -> str:
        """为无 DAG Edge 的顺序 Workflow 生成稳定 decision fingerprint。"""
        payload = "|".join((str(execution_id), str(version_id), ",".join(node_ids))).encode("utf-8")
        return sha256(payload).hexdigest()

    async def execute_frontier(self, frontier: WorkflowFrontier) -> None:
        """执行一个 Durable Frontier，并原子推进当前 Frontier 与后继 Frontier。

        Args:
            frontier: 已由当前 Worker Claim 且携带 fencing generation 的 Frontier。

        Returns:
            None。成功结果通过当前事务持久化；可重试失败由 Frontier Retry Contract 接管。

        Raises:
            HTTPException: Planner 与持久化 Frontier 不一致或 Runtime 无法继续执行时抛出。

        事务边界：Node Execution / Checkpoint、当前 Frontier terminal transition、Next Frontier enqueue
        与最终 Execution terminal transition 使用同一数据库事务。这里不创建第二套 Runtime。
        """
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
