"""Workflow Checkpoint Resume 候选评估单元测试。"""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.services.workflow import WorkflowExecutionService
from app.services.workflow.checkpoint.recovery import WorkflowExecutionCheckpointRecoveryService
from app.services.workflow.checkpoint.recovery.resume_bootstrap import _validate_resume_checkpoint_lineage
from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


def _checkpoint(
    *,
    execution_id,
    execution_status: str = "running",
    checkpoint_reason: str = "node.completed",
    node_status: str | None = "completed",
    node_id: str | None = "agent-1",
) -> WorkflowExecutionCheckpoint:
    """构造不依赖数据库的 Checkpoint 测试对象。"""
    return WorkflowExecutionCheckpoint(
        id=uuid4(),
        execution_id=execution_id,
        sequence=3,
        node_id=node_id,
        node_attempt=1 if node_id is not None else None,
        execution_status=execution_status,
        node_status=node_status,
        state_data={"cursor": "agent-2"},
        input_data={"prompt": "hello"},
        output_data={"text": "ok"},
        checkpoint_reason=checkpoint_reason,
        worker_owner="worker:old",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )


def test_assess_returns_eligible_candidate_for_failed_execution() -> None:
    """失败 Execution 且无活动 owner 时，完整 Node completed Checkpoint 可以形成恢复候选。"""
    execution_id = uuid4()
    version_id = uuid4()
    checkpoint = _checkpoint(execution_id=execution_id)

    assessment = WorkflowExecutionCheckpointRecoveryService.assess(
        execution_id=execution_id,
        workflow_version_id=version_id,
        execution_status="failed",
        worker_owner=None,
        checkpoint=checkpoint,
    )

    assert assessment.eligible is True
    assert assessment.reason_code == "eligible"
    assert assessment.execution_id == execution_id
    assert assessment.workflow_version_id == version_id
    assert assessment.checkpoint_sequence == 3
    assert assessment.node_id == "agent-1"
    assert assessment.state_data == {"cursor": "agent-2"}
    assert assessment.resume_idempotency_key == f"resume:{execution_id}:checkpoint:3"


def test_assess_accepts_execution_level_frontier_checkpoint() -> None:
    """Multi-frontier 的 Execution-level frontier checkpoint 也必须可作为 Resume 边界。"""
    execution_id = uuid4()
    version_id = uuid4()
    checkpoint = _checkpoint(
        execution_id=execution_id,
        checkpoint_reason="frontier_completed",
        node_status=None,
        node_id=None,
    )

    assessment = WorkflowExecutionCheckpointRecoveryService.assess(
        execution_id=execution_id,
        workflow_version_id=version_id,
        execution_status="failed",
        worker_owner=None,
        checkpoint=checkpoint,
    )

    assert assessment.eligible is True
    assert assessment.reason_code == "eligible"
    assert assessment.node_id is None


def test_assess_rejects_node_bound_frontier_checkpoint() -> None:
    """frontier_completed 如果携带 Node identity，必须拒绝，避免混淆 Multi-frontier 与 Node fact。"""
    execution_id = uuid4()
    version_id = uuid4()
    checkpoint = _checkpoint(
        execution_id=execution_id,
        checkpoint_reason="frontier_completed",
        node_status=None,
        node_id="branch-a",
    )

    assessment = WorkflowExecutionCheckpointRecoveryService.assess(
        execution_id=execution_id,
        workflow_version_id=version_id,
        execution_status="failed",
        worker_owner=None,
        checkpoint=checkpoint,
    )

    assert assessment.eligible is False
    assert assessment.reason_code == "checkpoint_boundary_invalid"


def test_assess_rejects_status_bound_frontier_checkpoint() -> None:
    """frontier_completed 如果携带 Node status，也必须拒绝恢复。"""
    execution_id = uuid4()
    version_id = uuid4()
    checkpoint = _checkpoint(
        execution_id=execution_id,
        checkpoint_reason="frontier_completed",
        node_status="completed",
        node_id=None,
    )

    assessment = WorkflowExecutionCheckpointRecoveryService.assess(
        execution_id=execution_id,
        workflow_version_id=version_id,
        execution_status="failed",
        worker_owner=None,
        checkpoint=checkpoint,
    )

    assert assessment.eligible is False
    assert assessment.reason_code == "checkpoint_boundary_invalid"


def test_assess_rejects_live_worker_ownership_and_running_execution() -> None:
    """恢复评估不得绕过 running Execution 或活动 Worker ownership。"""
    execution_id = uuid4()
    version_id = uuid4()
    checkpoint = _checkpoint(execution_id=execution_id)

    running = WorkflowExecutionCheckpointRecoveryService.assess(
        execution_id=execution_id,
        workflow_version_id=version_id,
        execution_status="running",
        worker_owner=None,
        checkpoint=checkpoint,
    )
    owned = WorkflowExecutionCheckpointRecoveryService.assess(
        execution_id=execution_id,
        workflow_version_id=version_id,
        execution_status="failed",
        worker_owner="worker:new",
        checkpoint=checkpoint,
    )

    assert running.eligible is False
    assert running.reason_code == "execution_not_failed"
    assert owned.eligible is False
    assert owned.reason_code == "worker_ownership_active"


def test_assess_rejects_missing_or_invalid_checkpoint_boundary() -> None:
    """没有 Checkpoint 或 Checkpoint 不是可恢复边界时禁止产生恢复候选。"""
    execution_id = uuid4()
    version_id = uuid4()

    missing = WorkflowExecutionCheckpointRecoveryService.assess(
        execution_id=execution_id,
        workflow_version_id=version_id,
        execution_status="failed",
        worker_owner=None,
        checkpoint=None,
    )
    invalid_reason = WorkflowExecutionCheckpointRecoveryService.assess(
        execution_id=execution_id,
        workflow_version_id=version_id,
        execution_status="failed",
        worker_owner=None,
        checkpoint=_checkpoint(execution_id=execution_id, checkpoint_reason="execution.failed"),
    )
    invalid_boundary = WorkflowExecutionCheckpointRecoveryService.assess(
        execution_id=execution_id,
        workflow_version_id=version_id,
        execution_status="failed",
        worker_owner=None,
        checkpoint=_checkpoint(execution_id=execution_id, node_status="failed"),
    )

    assert missing.reason_code == "checkpoint_missing"
    assert invalid_reason.reason_code == "checkpoint_not_resumable"
    assert invalid_boundary.reason_code == "checkpoint_boundary_invalid"


def test_assess_rejects_checkpoint_from_different_execution() -> None:
    """Recovery candidate 不得把其他 Execution 的 Checkpoint 作为当前 Replay snapshot。"""
    execution_id = uuid4()
    version_id = uuid4()
    checkpoint = _checkpoint(execution_id=uuid4())

    with pytest.raises(ValueError, match="跨 Execution Replay"):
        WorkflowExecutionCheckpointRecoveryService.assess(
            execution_id=execution_id,
            workflow_version_id=version_id,
            execution_status="failed",
            worker_owner=None,
            checkpoint=checkpoint,
        )


def test_assert_node_fact_complete_accepts_matching_durable_fact() -> None:
    """Node-level Checkpoint 与 Durable Node Fact 完全一致时允许进入 Recovery。"""
    checkpoint = _checkpoint(execution_id=uuid4())
    node_execution = SimpleNamespace(
        node_id="agent-1",
        status="completed",
        attempt=1,
        output_data={"text": "ok"},
    )

    WorkflowExecutionCheckpointService.assert_node_fact_complete(
        checkpoint=checkpoint,
        node_execution=node_execution,
    )


def test_assert_node_fact_complete_rejects_output_drift() -> None:
    """Checkpoint output 与 Durable Node Fact 漂移时必须拒绝 Recovery。"""
    checkpoint = _checkpoint(execution_id=uuid4())
    node_execution = SimpleNamespace(
        node_id="agent-1",
        status="completed",
        attempt=1,
        output_data={"text": "drifted"},
    )

    with pytest.raises(ValueError, match="output_data"):
        WorkflowExecutionCheckpointService.assert_node_fact_complete(
            checkpoint=checkpoint,
            node_execution=node_execution,
        )


def test_validate_resume_checkpoint_lineage_accepts_matching_sequence() -> None:
    """Resume 指向实际 Source Checkpoint 时允许继续 Bootstrap。"""
    _validate_resume_checkpoint_lineage(source_checkpoint_sequence=3, resume_checkpoint_sequence=3)


def test_validate_resume_checkpoint_lineage_rejects_missing_or_drifted_sequence() -> None:
    """Resume 未绑定 Source Checkpoint 或序号漂移时必须拒绝 Bootstrap。"""
    with pytest.raises(ValueError, match="缺少 Source Checkpoint"):
        _validate_resume_checkpoint_lineage(source_checkpoint_sequence=3, resume_checkpoint_sequence=None)
    with pytest.raises(ValueError, match="sequence 不一致"):
        _validate_resume_checkpoint_lineage(source_checkpoint_sequence=3, resume_checkpoint_sequence=4)


def test_validate_execution_fencing_accepts_matching_owner_and_generation() -> None:
    """Worker owner 与 fencing generation 同时匹配时允许继续 Durable 写入。"""
    WorkflowExecutionService._validate_execution_fencing(
        expected_worker_owner="worker:a",
        expected_worker_attempt=3,
        locked_worker_owner="worker:a",
        locked_worker_attempt=3,
    )


def test_validate_execution_fencing_rejects_stale_generation() -> None:
    """同一 Worker owner 在重新 claim 后 generation 变化时，旧执行上下文必须失效。"""
    with pytest.raises(HTTPException, match="fencing generation"):
        WorkflowExecutionService._validate_execution_fencing(
            expected_worker_owner="worker:a",
            expected_worker_attempt=3,
            locked_worker_owner="worker:a",
            locked_worker_attempt=4,
        )


def test_validate_execution_fencing_rejects_reclaimed_owner() -> None:
    """Execution 被其他 Worker reclaim 后，即使旧 generation 相同也必须拒绝。"""
    with pytest.raises(HTTPException, match="ownership"):
        WorkflowExecutionService._validate_execution_fencing(
            expected_worker_owner="worker:a",
            expected_worker_attempt=3,
            locked_worker_owner="worker:b",
            locked_worker_attempt=4,
        )
