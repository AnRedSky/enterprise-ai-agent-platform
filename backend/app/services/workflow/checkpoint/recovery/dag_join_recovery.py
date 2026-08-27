"""Workflow DAG Multi-frontier Join Recovery 领域校验模块。

职责：在 Durable Resume 时校验 Execution-level frontier Checkpoint 中的 merged state 是否与 Planner 选定的 Join predecessor durable facts 一致。
边界：只消费调用方已经读取的 Workflow Definition、completed Node facts 与 Checkpoint state；不读取数据库、不执行条件表达式、不启动 Runtime、不修改 Execution。
关键依赖：WorkflowDagResumePlanner 的 selected predecessor facts、WorkflowDagJoinReadinessService、WorkflowDagBranchStateMergeService。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Mapping

from app.services.workflow.checkpoint.recovery.dag_join import (
    WorkflowDagJoinReadiness,
    WorkflowDagJoinReadinessService,
)


class WorkflowDagJoinRecoveryService:
    """校验 Multi-frontier Recovery 的 Join merged state 与 durable predecessor facts 一致。"""

    @staticmethod
    def validate_checkpoint_state(
        *,
        definition: dict,
        node_id: str,
        completed_node_ids: set[str] | frozenset[str],
        node_outputs: Mapping[str, Mapping[str, object]],
        predecessor_node_ids: tuple[str, ...],
        checkpoint_state: Mapping[str, object],
    ) -> WorkflowDagJoinReadiness:
        """验证 Join frontier 对应的 Execution-level Checkpoint 是否可安全用于 Recovery。

        Args:
            definition: 已通过 DAG Contract 校验的 Workflow Definition。
            node_id: 当前待恢复的 Join Node ID。
            completed_node_ids: 已持久化并验证为 completed 的 Node ID 集合。
            node_outputs: completed Node 的持久化输出状态。
            predecessor_node_ids: Planner 为当前 Join 选定的直接 predecessor 快照。
            checkpoint_state: 最近一个 `frontier_completed` Execution-level Checkpoint 的 state。

        Returns:
            WorkflowDagJoinReadiness：重新由 durable predecessor facts 计算出的 Join readiness。

        Raises:
            ValueError: Join 未 ready、Checkpoint state 与重新计算的 merged state 不一致，或输入违反 Join Contract。

        事务边界：纯内存校验，不执行 commit、不修改任何持久化对象。
        """
        if not isinstance(checkpoint_state, Mapping):
            raise ValueError("DAG Join Recovery Checkpoint state 必须为对象")

        readiness = WorkflowDagJoinReadinessService.evaluate(
            definition=definition,
            node_id=node_id,
            completed_node_ids=completed_node_ids,
            node_outputs=node_outputs,
            predecessor_node_ids=predecessor_node_ids,
        )
        if not readiness.ready or readiness.state_data is None:
            raise ValueError(f"DAG Join Recovery Node {node_id} 尚未具备完整 predecessor durable facts")

        expected_state = deepcopy(readiness.state_data)
        actual_state = deepcopy(dict(checkpoint_state))
        if actual_state != expected_state:
            raise ValueError(f"DAG Join Recovery Node {node_id} 的 merged Checkpoint state 与 predecessor durable facts 不一致")
        return readiness
