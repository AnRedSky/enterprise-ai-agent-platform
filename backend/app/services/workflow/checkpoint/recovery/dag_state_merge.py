"""Workflow DAG Resume 分支状态合并模块。

职责：冻结多 frontier Resume 在重新进入 Runtime 前的分支状态合并规则。
边界：只做纯内存确定性合并，不读取数据库、不修改 Checkpoint、不执行 Node、不获取 Worker ownership。
关键依赖：DAG Contract；调用方必须提供已经从持久化 Checkpoint 验证过的分支状态快照。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class WorkflowDagBranchState:
    """一个已完成 DAG 分支提供给 Merge Contract 的状态快照。"""

    node_id: str
    state_data: Mapping[str, object]


@dataclass(frozen=True)
class WorkflowDagStateMergePlan:
    """多 frontier Resume 使用的确定性合并结果。"""

    branch_node_ids: tuple[str, ...]
    state_data: dict[str, object]


class WorkflowDagBranchStateMergeService:
    """按显式冲突拒绝规则合并多个已完成分支的状态。"""

    @staticmethod
    def merge(*, branches: tuple[WorkflowDagBranchState, ...]) -> WorkflowDagStateMergePlan:
        """合并分支状态并拒绝无法证明安全的键冲突。

        Args:
            branches: 已完成分支的状态快照；必须至少提供一个分支，Node ID 不得重复。

        Returns:
            按 Node ID 稳定排序后的分支列表及深拷贝后的合并状态。

        Raises:
            ValueError: 分支为空、Node ID 非法、状态不是对象或不同分支对同一键写入不同值。

        设计意图：多 frontier Resume 不能通过“后写覆盖先写”隐式决定业务结果。相同键只有在所有
        分支值相等时才允许收敛；不同值必须显式报错，交给后续 DAG Join/Conflict Contract 处理。
        该规则只定义顶层状态键的安全合并边界，不宣称能够自动解决嵌套对象、列表追加或业务语义冲突。
        """
        if not branches:
            raise ValueError("DAG Branch State Merge 至少需要一个分支")

        ordered = tuple(sorted(branches, key=lambda branch: branch.node_id))
        node_ids: set[str] = set()
        merged: dict[str, object] = {}

        for branch in ordered:
            if not isinstance(branch.node_id, str) or not branch.node_id:
                raise ValueError("DAG Branch node_id 必须为非空字符串")
            if branch.node_id in node_ids:
                raise ValueError(f"DAG Branch node_id 重复: {branch.node_id}")
            node_ids.add(branch.node_id)
            if not isinstance(branch.state_data, Mapping):
                raise ValueError(f"DAG Branch state_data 必须为对象: {branch.node_id}")

            for key, value in branch.state_data.items():
                if not isinstance(key, str) or not key:
                    raise ValueError("DAG Branch state_data key 必须为非空字符串")
                if key in merged and merged[key] != value:
                    raise ValueError(f"DAG Branch state_data 存在冲突键: {key}")
                merged[key] = deepcopy(value)

        return WorkflowDagStateMergePlan(
            branch_node_ids=tuple(branch.node_id for branch in ordered),
            state_data=deepcopy(merged),
        )
