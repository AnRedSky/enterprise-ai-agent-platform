from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


def _service() -> WorkflowExecutionCheckpointService:
    return WorkflowExecutionCheckpointService(MagicMock())


def test_frontier_completed_checkpoint_rejects_node_fact() -> None:
    with pytest.raises(ValueError, match="Execution-level boundary"):
        _service()._build(
            execution_id=uuid4(),
            frontier_id=uuid4(),
            sequence=1,
            execution_status="running",
            state_data={"merged": True},
            checkpoint_reason="frontier_completed",
            node_id="branch-a",
            node_attempt=1,
            node_status="completed",
        )


def test_frontier_completed_checkpoint_accepts_execution_boundary() -> None:
    checkpoint = _service()._build(
        execution_id=uuid4(),
        frontier_id=uuid4(),
        sequence=1,
        execution_status="running",
        state_data={"merged": True},
        checkpoint_reason="frontier_completed",
    )

    assert checkpoint.node_id is None
    assert checkpoint.node_attempt is None
    assert checkpoint.node_status is None


def test_node_completed_checkpoint_requires_node_id() -> None:
    with pytest.raises(ValueError, match="必须携带 node_id"):
        _service()._build(
            execution_id=uuid4(),
            frontier_id=None,
            sequence=1,
            execution_status="running",
            state_data={"content": "done"},
            checkpoint_reason="node.completed",
            node_status="completed",
        )
