from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


def _execution(*, owner="worker-a", attempt=7, lease_delta_seconds=30):
    return SimpleNamespace(
        worker_owner=owner,
        worker_attempt=attempt,
        worker_lease_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=lease_delta_seconds),
    )


def test_checkpoint_worker_fencing_accepts_active_owner_epoch_and_lease():
    WorkflowExecutionCheckpointService._validate_worker_fencing(
        expected_worker_owner="worker-a",
        expected_worker_attempt=7,
        execution=_execution(),
    )


@pytest.mark.parametrize(
    "execution,expected_owner,expected_attempt",
    [
        (_execution(owner="worker-b"), "worker-a", 7),
        (_execution(attempt=8), "worker-a", 7),
        (_execution(lease_delta_seconds=-1), "worker-a", 7),
        (_execution(lease_delta_seconds=0), "worker-a", 7),
    ],
)
def test_checkpoint_worker_fencing_rejects_stale_owner_epoch_or_lease(
    execution, expected_owner, expected_attempt
):
    with pytest.raises(HTTPException) as exc_info:
        WorkflowExecutionCheckpointService._validate_worker_fencing(
            expected_worker_owner=expected_owner,
            expected_worker_attempt=expected_attempt,
            execution=execution,
        )
    assert exc_info.value.status_code == 409
