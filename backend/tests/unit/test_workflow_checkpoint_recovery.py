"""Workflow Checkpoint Resume 候选评估单元测试。"""

from datetime import datetime
from uuid import uuid4

from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.services.workflow.checkpoint.recovery import WorkflowExecutionCheckpointRecoveryService


def _checkpoint(
    *,
    execution_id,
    execution_status: str = "running",
    checkpoint_reason: str = "node.completed",
    node_status: str = "completed",
    node_id: str | None = "agent-1",
) -> WorkflowExecutionCheckpoint:
    """构造不依赖数据库的 Checkpoint 测试对象。"""
    return WorkflowExecutionCheckpoint(
        id=uuid4(),
        execution_id=execution_id,
        sequence=3,
        node_id=node_id,
        node_attempt=1,
        execution_status=execution_status,
        node_status=node_status,
        state_data={"cursor": "agent-2"},
        input_data={"prompt": "hello"},
        output_data={"text": "ok"},
        checkpoint_reason=checkpoint_reason,
        worker_owner="worker:old",
        created_at=datetime.utcnow(),
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
    """没有 Checkpoint 或 Checkpoint 不是 Node completed 边界时禁止产生恢复候选。"""
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
