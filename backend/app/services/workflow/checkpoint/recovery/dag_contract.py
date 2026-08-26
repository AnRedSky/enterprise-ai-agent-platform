"""Workflow DAG Resume Contract 校验模块。

职责：冻结并校验 Phase 2.6 第一版 DAG Resume 所依赖的图结构 Contract。
边界：只做纯内存结构与拓扑校验，不读取数据库、不推断 Node 完成事实、不生成 Resume frontier、不执行 Runtime。
关键依赖：Workflow Definition 的 nodes / edges 结构。
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowDagEdge:
    """经过 Contract 校验的有向边。"""

    source: str
    target: str


@dataclass(frozen=True)
class WorkflowDagContract:
    """经过 Contract 校验的 DAG 图快照。"""

    node_ids: tuple[str, ...]
    edges: tuple[WorkflowDagEdge, ...]
    roots: tuple[str, ...]


class WorkflowDagContractValidator:
    """校验 DAG Resume 第一版允许使用的 Workflow Definition 图结构。"""

    @staticmethod
    def validate(*, definition: dict) -> WorkflowDagContract:
        """校验并冻结 DAG Definition 的结构与拓扑安全边界。

        Args:
            definition: Workflow Version 的完整 Definition，必须包含 nodes 与非空 edges。

        Returns:
            只包含稳定 Node ID、Edge 以及根节点的不可变 DAG Contract。

        Raises:
            ValueError: Definition、Node ID、Edge、重复边、孤立节点或拓扑结构不满足 Contract。

        设计意图：当前顺序 Runtime 可以接受空 edges，但 DAG Resume 必须显式进入图模式；因此本校验器
        不修改现有顺序 Resume 行为，也不在没有正式图 Contract 时偷偷解释 edges。第一版只接受单一根节点，
        不接受条件边或多根图，不承诺并行执行，frontier 完成事实仍必须来自 Source Execution 持久化
        Node Execution / Checkpoint。
        """
        if not isinstance(definition, dict):
            raise ValueError("DAG Workflow definition 必须为对象")

        nodes = definition.get("nodes")
        edges = definition.get("edges")
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("DAG Workflow 必须包含非空 nodes")
        if not isinstance(edges, list) or not edges:
            raise ValueError("DAG Workflow 必须包含非空 edges")

        node_ids: list[str] = []
        node_id_set: set[str] = set()
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError("DAG Node 必须为对象")
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                raise ValueError("DAG Node id 必须为非空字符串")
            if node_id in node_id_set:
                raise ValueError(f"DAG Node id 重复: {node_id}")
            node_id_set.add(node_id)
            node_ids.append(node_id)

        parsed_edges: list[WorkflowDagEdge] = []
        edge_set: set[tuple[str, str]] = set()
        outgoing: dict[str, list[str]] = defaultdict(list)
        incoming_count: dict[str, int] = {node_id: 0 for node_id in node_ids}

        for edge in edges:
            if not isinstance(edge, dict) or set(edge) != {"source", "target"}:
                raise ValueError("DAG Edge 必须只包含 source / target 字段")
            source = edge.get("source")
            target = edge.get("target")
            if not isinstance(source, str) or not source or not isinstance(target, str) or not target:
                raise ValueError("DAG Edge source / target 必须为非空字符串")
            if source not in node_id_set or target not in node_id_set:
                raise ValueError("DAG Edge 必须引用已存在的 Node")
            if source == target:
                raise ValueError("DAG Edge 不允许 self-loop")
            key = (source, target)
            if key in edge_set:
                raise ValueError(f"DAG Edge 重复: {source} -> {target}")
            edge_set.add(key)
            parsed_edges.append(WorkflowDagEdge(source=source, target=target))
            outgoing[source].append(target)
            incoming_count[target] += 1

        isolated = [node_id for node_id in node_ids if not outgoing[node_id] and incoming_count[node_id] == 0]
        if isolated:
            raise ValueError(f"DAG 不允许孤立 Node: {isolated[0]}")

        roots = tuple(node_id for node_id in node_ids if incoming_count[node_id] == 0)
        if len(roots) != 1:
            raise ValueError("DAG Workflow 第一版 Resume 必须只有一个 root")

        queue = deque(roots)
        visited_count = 0
        remaining_incoming = dict(incoming_count)
        while queue:
            source = queue.popleft()
            visited_count += 1
            for target in outgoing[source]:
                remaining_incoming[target] -= 1
                if remaining_incoming[target] == 0:
                    queue.append(target)

        if visited_count != len(node_ids):
            raise ValueError("DAG Workflow 不允许存在循环")

        return WorkflowDagContract(
            node_ids=tuple(node_ids),
            edges=tuple(parsed_edges),
            roots=roots,
        )
