from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


def _execution(*, owner: str | None, attempt: int) -> MagicMock:
    execution = MagicMock()
    execution.worker_owner = owner
    execution.worker_attempt = attempt
    execution.worker_lease_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)
    return execution


def test_checkpoint_worker_fencing_accepts_matching_generation() -> None:
    execution = _execution(owner="worker-a", attempt=4)

    WorkflowExecutionCheckpointService._validate_worker_fencing(
        expected_worker_owner="worker-a",
        expected_worker_attempt=4,
        execution=execution,
    )


def test_checkpoint_worker_fencing_rejects_stale_generation() -> None:
    execution = _execution(owner="worker-a", attempt=5)

    with pytest.raises(HTTPException, match="fencing generation 已失效"):
        WorkflowExecutionCheckpointService._validate_worker_fencing(
            expected_worker_owner="worker-a",
            expected_worker_attempt=4,
            execution=execution,
        )


def test_checkpoint_worker_fencing_rejects_reclaimed_owner() -> None:
    execution = _execution(owner="worker-b", attempt=5)

    with pytest.raises(HTTPException, match="Worker ownership 或 fencing generation 已失效"):
        WorkflowExecutionCheckpointService._validate_worker_fencing(
            expected_worker_owner="worker-a",
            expected_worker_attempt=5,
            execution=execution,
        )


def test_checkpoint_worker_fencing_requires_complete_expected_generation() -> None:
    execution = _execution(owner="worker-a", attempt=4)

    with pytest.raises(HTTPException, match="参数不完整"):
        WorkflowExecutionCheckpointService._validate_worker_fencing(
            expected_worker_owner="worker-a",
            expected_worker_attempt=None,
            execution=execution,
        )
