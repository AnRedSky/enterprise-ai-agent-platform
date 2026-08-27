"""Workflow Checkpoint Execution lifecycle Contract 单元测试。"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


def test_checkpoint_lifecycle_allows_matching_execution_status() -> None:
    execution = SimpleNamespace(status="completed")

    WorkflowExecutionCheckpointService._validate_execution_status_boundary(
        execution=execution,
        execution_status="completed",
    )


def test_checkpoint_lifecycle_rejects_stale_worker_status() -> None:
    execution = SimpleNamespace(status="completed")

    with pytest.raises(HTTPException, match="Execution status 已变化"):
        WorkflowExecutionCheckpointService._validate_execution_status_boundary(
            execution=execution,
            execution_status="running",
        )


def test_checkpoint_lifecycle_rejects_terminal_to_pending_snapshot() -> None:
    execution = SimpleNamespace(status="failed")

    with pytest.raises(HTTPException, match="current=failed, requested=pending"):
        WorkflowExecutionCheckpointService._validate_execution_status_boundary(
            execution=execution,
            execution_status="pending",
        )
