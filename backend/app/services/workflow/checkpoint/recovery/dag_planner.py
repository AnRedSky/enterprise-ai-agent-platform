"""Workflow DAG Resume Frontier 规划模块。

职责：根据已持久化完成 Node 集合与冻结后的 DAG Contract，计算下一批可恢复 Node。
边界：只做纯内存计算，不读取数据库、不合并 state_data、不执行 Runtime、不获取 Worker ownership。
关键依赖：WorkflowDagContractValidator；完成事实必须由调用方从持久化 Node Execution / Checkpoint 提供。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.workflow.checkpoint.recovery.dag_contract import WorkflowDagContractValidator


@dataclass(frozen=True)
class WorkflowDagResumePlan:
    """DAG Resume 的确定性 frontier 计划。"""

    completed_node_ids: tuple[str, ...]
    frontier_node_ids: tuple[str, ...]


class WorkflowDagResumePlanner:
    """根据已完成 Node 计算下一批所有 predecessor 均完成的 frontier。"""

    @staticmethod
    def plan(*, definition: dict, completed_node_ids: set[str] | frozenset[str]) -> WorkflowDagResumePlan:
        """计算 DAG Resume frontier。

        Args:
            definition: 已冻结的 Workflow Version DAG Definition。
            completed_node_ids: 外部已经验证的持久化完成事实集合。

        Returns:
            按 Definition.nodes 顺序返回确定性 completed 与 frontier Node 集合。

        Raises:
            ValueError: 完成事实类型、Node 引用或祖先完成关系不满足 DAG Resume Contract。

        设计意图：第一版 Runtime 是顺序恢复，因此持久化完成事实必须形成从唯一 root 向下的闭包。
        如果某个已完成 Node 的 predecessor 尚未完成，则该事实不能安全进入当前 Resume frontier；拒绝它
        可以避免把不可能由当前顺序 Runtime 产生的数据库状态当成合法恢复输入。
        """
        contract = WorkflowDagContractValidator.validate(definition=definition)
        if not isinstance(completed_node_ids, (set, frozenset)):
            raise ValueError("DAG Resume completed_node_ids 必须为 set 或 frozenset")
        if not all(isinstance(node_id, str) and node_id for node_id in completed_node_ids):
            raise ValueError("DAG Resume completed_node_ids 必须只包含非空字符串")

        node_id_set = set(contract.node_ids)
        unknown_completed = completed_node_ids - node_id_set
        if unknown_completed:
            raise ValueError(f"DAG Resume 存在未知 completed Node: {sorted(unknown_completed)[0]}")

        predecessors: dict[str, set[str]] = {node_id: set() for node_id in contract.node_ids}
        for edge in contract.edges:
            predecessors[edge.target].add(edge.source)

        invalid_completed = sorted(
            node_id
            for node_id in completed_node_ids
            if not predecessors[node_id].issubset(completed_node_ids)
        )
        if invalid_completed:
            raise ValueError(
                f"DAG Resume completed Node 缺少已完成 predecessor: {invalid_completed[0]}"
            )

        frontier = tuple(
            node_id
            for node_id in contract.node_ids
            if node_id not in completed_node_ids
            and predecessors[node_id].issubset(completed_node_ids)
        )
        return WorkflowDagResumePlan(
            completed_node_ids=tuple(node_id for node_id in contract.node_ids if node_id in completed_node_ids),
            frontier_node_ids=frontier,
        )
