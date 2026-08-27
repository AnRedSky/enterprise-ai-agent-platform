"""Workflow DAG 分支状态合并单元测试。

职责：验证多 frontier Resume 的确定性 Merge Contract。
边界：只验证纯内存规则，不启动 Runtime、不访问数据库。
"""

import pytest

from app.services.workflow.checkpoint.recovery.dag_state_merge import (
    WorkflowDagBranchState,
    WorkflowDagBranchStateMergeService,
)


def test_merge_is_deterministic_and_preserves_equal_values() -> None:
    result = WorkflowDagBranchStateMergeService.merge(
        branches=(
            WorkflowDagBranchState("branch-b", {"shared": 1, "b": {"value": 2}}),
            WorkflowDagBranchState("branch-a", {"shared": 1, "a": [1, 2]}),
        )
    )

    assert result.branch_node_ids == ("branch-a", "branch-b")
    assert result.state_data == {"shared": 1, "a": [1, 2], "b": {"value": 2}}


def test_merge_rejects_conflicting_top_level_state_key() -> None:
    with pytest.raises(ValueError, match="存在冲突键: result"):
        WorkflowDagBranchStateMergeService.merge(
            branches=(
                WorkflowDagBranchState("branch-a", {"result": "a"}),
                WorkflowDagBranchState("branch-b", {"result": "b"}),
            )
        )


def test_merge_rejects_duplicate_branch() -> None:
    with pytest.raises(ValueError, match="node_id 重复"):
        WorkflowDagBranchStateMergeService.merge(
            branches=(
                WorkflowDagBranchState("branch-a", {"a": 1}),
                WorkflowDagBranchState("branch-a", {"b": 2}),
            )
        )


def test_merge_requires_branch() -> None:
    with pytest.raises(ValueError, match="至少需要一个分支"):
        WorkflowDagBranchStateMergeService.merge(branches=())
