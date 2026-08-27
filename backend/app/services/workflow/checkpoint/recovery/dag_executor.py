"""Workflow DAG Multi-frontier Resume 执行协调模块。

职责：在已经生成的 Multi-frontier Runtime Plan 上定义 Branch 执行、结果收集、Branch Checkpoint 持久化边界、Join readiness 与状态合并的领域边界。
边界：不创建 Worker ownership、不直接修改 Workflow Execution ORM；实际 Node 执行与 Checkpoint 持久化通过调用方注入的 async callback 完成。
关键依赖：WorkflowDagResumeRuntimePlan、WorkflowDagBranchStateMergeService。

设计约束：
1. 当前采用单 Worker 内的确定性顺序 Branch 执行，不伪装成多 Worker 并行；
2. 每个 frontier Branch 使用自己的 state_data，禁止共享可变 state；
3. 任一 Branch 失败立即停止后续 Branch，Join 不可就绪；
4. Branch 执行成功后必须先完成 Branch Checkpoint callback，才能进入最终 Join readiness；
5. 只有所有 frontier Branch 执行与 Checkpoint 都成功后才允许生成 merged state；
6. Join readiness 是纯领域事实：`all_frontier_completed_and_checkpointed == True`，不负责调度 Join Node；
7. Executor 不直接写数据库；Checkpoint callback 必须由 WorkflowExecutionService / Checkpoint Service 在现有 Worker ownership、fencing 与事务边界内实现。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Awaitable, Callable, Mapping

from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlan
from app.services.workflow.checkpoint.recovery.dag_state_merge import (
    WorkflowDagBranchState,
    WorkflowDagBranchStateMergeService,
)


@dataclass(frozen=True)
class WorkflowDagBranchExecutionResult:
    """单个 frontier Branch 的执行事实。"""

    node_id: str
    state_data: dict


@dataclass(frozen=True)
class WorkflowDagMultiFrontierExecutionResult:
    """Multi-frontier 执行结果；Join 只能消费全部 Branch 成功且 Checkpoint 完成后的结果。"""

    branch_results: tuple[WorkflowDagBranchExecutionResult, ...]
    merged_state_data: dict | None
    join_ready: bool


BranchExecutor = Callable[[dict, dict], Awaitable[dict]]
BranchCheckpointWriter = Callable[[str, dict], Awaitable[None]]


class WorkflowDagMultiFrontierExecutor:
    """协调当前 Runtime Plan 的多 frontier Branch 执行与 Checkpoint 边界。"""

    @staticmethod
    async def execute(
        plan: WorkflowDagResumeRuntimePlan,
        *,
        branch_state_data: Mapping[str, Mapping[str, object]],
        executor: BranchExecutor,
        checkpoint_writer: BranchCheckpointWriter | None = None,
    ) -> WorkflowDagMultiFrontierExecutionResult:
        """按确定性 frontier 顺序执行 Branch，并在全部执行/Checkpoint 成功后计算 Join readiness。

        `executor(node, state_data)` 必须返回新的 state 对象；输入 state 会先 deep-copy，避免一个
        Branch 的 Runtime 修改污染另一个 Branch。`checkpoint_writer(node_id, state_data)` 是持久化
        边界；未提供 writer 时可以执行并收集 Branch 结果，但绝不能声明 Join ready，因为成功的
        Branch Checkpoint 是 Join readiness 的必要条件。该 callback 必须在现有 Worker ownership /
        fencing / transaction 体系中实现。

        本方法不捕获 Branch 或 Checkpoint 异常，因为失败必须直接阻止后续 Branch 与 Join readiness，
        并由上层 Worker / ExecutionService 负责统一失败状态转换。
        """
        if not plan.frontier_node_ids:
            return WorkflowDagMultiFrontierExecutionResult((), None, False)
        if len(plan.frontier_node_ids) == 1:
            node_id = plan.frontier_node_ids[0]
            source_state = branch_state_data.get(node_id, plan.state_data)
            output = await executor(deepcopy(plan.nodes[0]), deepcopy(dict(source_state)))
            if not isinstance(output, dict):
                raise ValueError(f"DAG frontier Node {node_id} 执行结果必须为对象")
            result = WorkflowDagBranchExecutionResult(node_id=node_id, state_data=deepcopy(output))
            checkpointed = checkpoint_writer is not None
            if checkpoint_writer is not None:
                await checkpoint_writer(node_id, deepcopy(output))
            return WorkflowDagMultiFrontierExecutionResult(
                (result,),
                deepcopy(output) if checkpointed else None,
                checkpointed,
            )

        missing = [node_id for node_id in plan.frontier_node_ids if node_id not in branch_state_data]
        unknown = [node_id for node_id in branch_state_data if node_id not in plan.frontier_node_ids]
        if missing:
            raise ValueError(f"DAG Multi-frontier 执行缺少 Branch state: {missing[0]}")
        if unknown:
            raise ValueError(f"DAG Multi-frontier 执行存在非 frontier Branch state: {unknown[0]}")

        results: list[WorkflowDagBranchExecutionResult] = []
        checkpointed = checkpoint_writer is not None
        for index, node_id in enumerate(plan.frontier_node_ids):
            output = await executor(
                deepcopy(plan.nodes[index]),
                deepcopy(dict(branch_state_data[node_id])),
            )
            if not isinstance(output, dict):
                raise ValueError(f"DAG frontier Node {node_id} 执行结果必须为对象")
            branch_result = WorkflowDagBranchExecutionResult(
                node_id=node_id,
                state_data=deepcopy(output),
            )
            if checkpoint_writer is not None:
                await checkpoint_writer(node_id, deepcopy(output))
            results.append(branch_result)

        if not checkpointed:
            return WorkflowDagMultiFrontierExecutionResult(
                branch_results=tuple(results),
                merged_state_data=None,
                join_ready=False,
            )

        merge_plan = WorkflowDagBranchStateMergeService.merge(
            branches=tuple(
                WorkflowDagBranchState(node_id=result.node_id, state_data=result.state_data)
                for result in results
            )
        )
        return WorkflowDagMultiFrontierExecutionResult(
            branch_results=tuple(results),
            merged_state_data=merge_plan.state_data,
            join_ready=True,
        )
