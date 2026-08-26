"""Workflow DAG Resume Runtime 计划模块。

职责：把纯内存 DAG Resume Frontier 转换为 Runtime 可以消费的确定性 Node 计划。
边界：不读取数据库、不创建 Node Execution、不修改 Checkpoint、不获取 Worker ownership；已完成 Node 事实必须由调用方从持久化来源提供。
关键依赖：WorkflowDagResumePlanner；Runtime 第一版仅允许单一 frontier Node，避免在分支状态合并规则冻结前伪装支持并行或隐式 merge。
"""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy

from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlanner


@dataclass(frozen=True)
class WorkflowDagResumeRuntimePlan:
    """DAG Resume Runtime 的确定性单 Node 执行计划。"""

    completed_node_ids: tuple[str, ...]
    frontier_node_id: str
    node: dict
    state_data: dict


class WorkflowDagResumeRuntimePlanner:
    """将 DAG Resume frontier 收敛为当前 Runtime 可安全消费的单节点计划。"""

    @staticmethod
    def plan(
        *,
        definition: dict,
        completed_node_ids: set[str] | frozenset[str],
        state_data: dict,
    ) -> WorkflowDagResumeRuntimePlan:
        """生成当前 Runtime 可以执行的 DAG Resume 单节点计划。

        Args:
            definition: 固定 Workflow Version 的 DAG Definition。
            completed_node_ids: 调用方从 Source Execution 持久化 Node Execution 得到的已完成 Node ID 集合。
            state_data: 最新可恢复 Checkpoint 的业务状态快照。

        Returns:
            包含确定性 frontier Node、节点定义和独立状态快照的 Runtime 计划。

        Raises:
            ValueError: Definition、完成事实或 state_data 不符合 DAG Resume Contract，或当前 frontier
                同时存在多个 Node 时抛出，避免在分支状态合并规则未冻结前产生隐式数据覆盖。

        设计边界：第一版 Runtime 不宣称并行恢复。单一 frontier 可以安全进入现有 Node Runtime；
        多 frontier 必须等待明确的分支状态合并 Contract，不能把前一个分支的输出偷偷作为后一个分支的输入。
        """
        if not isinstance(state_data, dict):
            raise ValueError("DAG Resume Runtime state_data 必须为对象")

        plan = WorkflowDagResumePlanner.plan(
            definition=definition,
            completed_node_ids=completed_node_ids,
        )
        if len(plan.frontier_node_ids) != 1:
            raise ValueError(
                "DAG Resume Runtime 当前只允许单一 frontier Node，多个 frontier 分支需要先冻结状态合并 Contract"
            )

        frontier_node_id = plan.frontier_node_ids[0]
        node = next(
            node for node in definition["nodes"]
            if isinstance(node, dict) and node.get("id") == frontier_node_id
        )
        return WorkflowDagResumeRuntimePlan(
            completed_node_ids=plan.completed_node_ids,
            frontier_node_id=frontier_node_id,
            node=deepcopy(node),
            state_data=deepcopy(state_data),
        )
