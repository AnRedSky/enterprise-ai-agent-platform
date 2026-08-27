"""Checkpoint Durable Fact 完整性的单元测试。"""

from types import SimpleNamespace

import pytest

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


def _checkpoint(**overrides):
    values = {"node_id": "node-a", "node_status": "succeeded", "node_attempt": 2, "output_data": {"value": 3}}
    values.update(overrides)
    return SimpleNamespace(**values)


def _node_execution(**overrides):
    values = {"node_id": "node-a", "status": "succeeded", "attempt": 2, "output_data": {"value": 3}}
    values.update(overrides)
    return SimpleNamespace(**values)


def test_checkpoint_node_fact_matches_node_execution() -> None:
    WorkflowExecutionCheckpointService.assert_node_fact_complete(
        checkpoint=_checkpoint(), node_execution=_node_execution()
    )


def test_checkpoint_node_fact_rejects_status_mismatch() -> None:
    with pytest.raises(ValueError, match="node status"):
        WorkflowExecutionCheckpointService.assert_node_fact_complete(
            checkpoint=_checkpoint(), node_execution=_node_execution(status="failed")
        )


def test_checkpoint_node_fact_rejects_attempt_mismatch() -> None:
    with pytest.raises(ValueError, match="attempt"):
        WorkflowExecutionCheckpointService.assert_node_fact_complete(
            checkpoint=_checkpoint(), node_execution=_node_execution(attempt=1)
        )


def test_checkpoint_node_fact_rejects_output_mismatch() -> None:
    with pytest.raises(ValueError, match="output_data"):
        WorkflowExecutionCheckpointService.assert_node_fact_complete(
            checkpoint=_checkpoint(), node_execution=_node_execution(output_data={"value": 4})
        )


def test_execution_level_checkpoint_does_not_require_node_fact() -> None:
    WorkflowExecutionCheckpointService.assert_node_fact_complete(
        checkpoint=_checkpoint(node_id=None, node_status=None, node_attempt=None, output_data=None),
        node_execution=None,
    )


def test_node_checkpoint_requires_corresponding_node_execution() -> None:
    with pytest.raises(ValueError, match="NodeExecution"):
        WorkflowExecutionCheckpointService.assert_node_fact_complete(
            checkpoint=_checkpoint(), node_execution=None
        )
