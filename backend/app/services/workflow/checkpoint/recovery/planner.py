"""Workflow Durable Resume 运行计划模块。

职责：把已验证的 Checkpoint 恢复边界转换成当前 Runtime 可执行的剩余节点定义。
边界：只做纯内存计算，不读取或写入数据库，不修改 Execution/Node 状态，不执行 Runtime。
关键约束：当前 Runtime 只按 nodes 顺序执行，因此本 Planner 只允许从明确存在的 checkpoint node 之后继续，不宣称支持未实现的 DAG 分支恢复。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowResumePlan:
    """已完成 Checkpoint 对应的 Runtime 恢复计划。"""

    checkpoint_node_id: str
    checkpoint_sequence: int
    state_data: dict
    remaining_nodes: tuple[dict, ...]


class WorkflowExecutionResumePlanner:
    """根据已完成 Node Checkpoint 生成后续顺序节点计划。"""

    @staticmethod
    def plan(
        *,
        definition: dict,
        checkpoint_node_id: str,
        checkpoint_sequence: int,
        state_data: dict,
    ) -> WorkflowResumePlan:
        """计算从 Checkpoint 后继续执行所需的剩余节点。

        Args:
            definition: 原 Workflow Version 的完整 Definition。
            checkpoint_node_id: 已完成并形成 Checkpoint 的 Node ID。
            checkpoint_sequence: Checkpoint 在原 Execution 中的递增序号。
            state_data: Checkpoint 保存的可恢复业务状态。

        Returns:
            包含恢复状态与后续节点快照的不可变 Resume Plan。

        Raises:
            ValueError: Definition、Checkpoint Node 或序号不满足当前顺序 Runtime 的恢复契约。

        设计边界：当前 WorkflowRuntime 按 nodes 数组顺序执行，因此只从该 Node 在数组中的
        下一位置继续。未来引入 DAG Runtime 后，必须由新的图恢复规划器替换此实现，禁止在这里
        通过复制边计算逻辑伪装支持分支恢复。
        """
        if not isinstance(definition, dict):
            raise ValueError("Workflow definition 必须为对象")
        nodes = definition.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("Resume Workflow 必须包含非空 nodes")
        if not isinstance(checkpoint_node_id, str) or not checkpoint_node_id:
            raise ValueError("Checkpoint node_id 无效")
        if isinstance(checkpoint_sequence, bool) or not isinstance(checkpoint_sequence, int) or checkpoint_sequence < 0:
            raise ValueError("Checkpoint sequence 无效")
        if not isinstance(state_data, dict):
            raise ValueError("Checkpoint state_data 必须为对象")

        positions = [index for index, node in enumerate(nodes) if isinstance(node, dict) and node.get("id") == checkpoint_node_id]
        if len(positions) != 1:
            raise ValueError("Checkpoint node_id 必须在 Workflow Definition 中唯一存在")

        checkpoint_index = positions[0]
        remaining_nodes = tuple(deepcopy(nodes[checkpoint_index + 1 :]))
        return WorkflowResumePlan(
            checkpoint_node_id=checkpoint_node_id,
            checkpoint_sequence=checkpoint_sequence,
            state_data=deepcopy(state_data),
            remaining_nodes=remaining_nodes,
        )
