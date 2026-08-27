"""DAG Resume Frontier progression 适配模块。

职责：把当前 Multi-frontier Runtime 完成后的持久化事实重新交给唯一 DAG Planner，生成下一 Frontier 的确定性身份，并在同一外层事务内交给统一 Frontier progression contract 持久化。
边界：不执行 Node、不获取 Worker ownership；Planner 负责计算，frontier_progression 负责 Frontier → Checkpoint → Next Frontier 原子持久化。
关键依赖：WorkflowDagResumePlanner、WorkflowDagResumeRuntimePlan、WorkflowFrontierIdentity、complete_frontier_with_checkpoint。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowFrontier
from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlan, WorkflowDagResumePlanner
from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlan
from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_progression import complete_frontier_with_checkpoint


@dataclass(frozen=True)
class WorkflowDagNextFrontierPlan:
    """当前 Frontier 完成后下一 Frontier 的确定性规划结果。"""

    resume_plan: WorkflowDagResumePlan
    identity: WorkflowFrontierIdentity | None


@dataclass(frozen=True)
class WorkflowDagFrontierProgressionResult:
    """DAG Frontier 从 Planner 到 Durable Frontier 的完整事务结果。"""

    plan: WorkflowDagNextFrontierPlan
    checkpoint: object
    next_frontier: WorkflowFrontier | None


class WorkflowDagFrontierProgressionService:
    """将 Durable Checkpoint 之后的完成事实收敛为下一 Frontier，并复用统一原子持久化 Contract。"""

    @staticmethod
    def plan_next_frontier(
        *,
        definition: dict,
        execution_id: UUID,
        workflow_version_id: UUID,
        current_plan: WorkflowDagResumeRuntimePlan,
        completed_node_ids: set[str] | frozenset[str],
        state_data_by_node: dict[str, dict],
    ) -> WorkflowDagNextFrontierPlan:
        """根据当前 Frontier 完成后的持久化事实生成下一 Frontier。"""
        if not current_plan.frontier_node_ids:
            raise ValueError("当前 Runtime Plan 必须至少包含一个 frontier")
        completed = set(completed_node_ids)
        missing_current = set(current_plan.frontier_node_ids) - completed
        if missing_current:
            raise ValueError(f"当前 frontier 尚未全部形成 completed durable facts: {sorted(missing_current)[0]}")
        if not isinstance(state_data_by_node, dict):
            raise ValueError("下一 Frontier planning 的 state_data_by_node 必须为对象")
        unknown_state = set(state_data_by_node) - completed
        if unknown_state:
            raise ValueError(f"state_data_by_node 存在未完成 Node: {sorted(unknown_state)[0]}")

        resume_plan = WorkflowDagResumePlanner.plan(
            definition=definition,
            completed_node_ids=frozenset(completed),
            state_data_by_node=state_data_by_node,
        )
        if not resume_plan.frontier_node_ids:
            return WorkflowDagNextFrontierPlan(resume_plan=resume_plan, identity=None)

        node_ids = {
            node.get("id")
            for node in definition.get("nodes", [])
            if isinstance(node, dict) and isinstance(node.get("id"), str)
        }
        unknown_frontier = set(resume_plan.frontier_node_ids) - node_ids
        if unknown_frontier:
            raise ValueError(f"下一 Frontier 引用了未知 Node: {sorted(unknown_frontier)[0]}")

        identity = WorkflowFrontierIdentity(
            execution_id=execution_id,
            workflow_version_id=workflow_version_id,
            decision_fingerprint=resume_plan.decision_fingerprint,
            node_ids=resume_plan.frontier_node_ids,
        )
        return WorkflowDagNextFrontierPlan(resume_plan=resume_plan, identity=identity)

    @classmethod
    async def complete_frontier(
        cls,
        db: AsyncSession,
        *,
        frontier: WorkflowFrontier,
        worker_owner: str,
        attempt: int,
        definition: dict,
        current_plan: WorkflowDagResumeRuntimePlan,
        completed_node_ids: set[str] | frozenset[str],
        state_data_by_node: dict[str, dict],
        checkpoint_state: dict,
        checkpoint_reason: str,
        now: datetime,
        node_id: str | None = None,
        node_attempt: int | None = None,
        node_status: str | None = None,
        input_data: dict | None = None,
        output_data: dict | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> WorkflowDagFrontierProgressionResult:
        """在统一事务中完成 DAG Frontier → Checkpoint → Next Frontier。

        Planner 只负责计算下一 Frontier identity；真正持久化必须统一经过
        ``complete_frontier_with_checkpoint``，避免 Runtime 自己 enqueue Frontier 形成旁路。
        方法本身不 commit，事务失败由调用方 rollback。
        """
        next_plan = cls.plan_next_frontier(
            definition=definition,
            execution_id=frontier.execution_id,
            workflow_version_id=frontier.workflow_version_id,
            current_plan=current_plan,
            completed_node_ids=completed_node_ids,
            state_data_by_node=state_data_by_node,
        )
        checkpoint, next_frontier = await complete_frontier_with_checkpoint(
            db,
            frontier=frontier,
            worker_owner=worker_owner,
            attempt=attempt,
            checkpoint_state=checkpoint_state,
            checkpoint_reason=checkpoint_reason,
            node_id=node_id,
            node_attempt=node_attempt,
            node_status=node_status,
            input_data=input_data,
            output_data=output_data,
            error_code=error_code,
            error_message=error_message,
            next_identity=next_plan.identity,
            now=now,
        )
        return WorkflowDagFrontierProgressionResult(
            plan=next_plan,
            checkpoint=checkpoint,
            next_frontier=next_frontier,
        )
