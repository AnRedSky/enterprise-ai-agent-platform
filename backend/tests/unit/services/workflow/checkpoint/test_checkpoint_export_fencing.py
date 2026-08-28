import pytest

from app.services.workflow.checkpoint import WorkflowExecutionCheckpointService
from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService as BaseCheckpointService


@pytest.mark.asyncio
async def test_manual_checkpoint_write_does_not_pass_default_worker_attempt(monkeypatch):
    captured = {}

    async def fake_append(self, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(BaseCheckpointService, "append_next_in_transaction", fake_append)

    service = WorkflowExecutionCheckpointService(None)
    result = await service.append_next_in_transaction(
        execution_id="execution",
        execution_status="running",
        state_data={},
        checkpoint_reason="node.completed",
        node_id="node",
        node_attempt=1,
        node_status="completed",
        expected_worker_owner=None,
        expected_worker_attempt=0,
    )

    assert result is not None
    assert captured["expected_worker_owner"] is None
    assert captured["expected_worker_attempt"] is None


@pytest.mark.asyncio
async def test_worker_checkpoint_fencing_generation_is_preserved(monkeypatch):
    captured = {}

    async def fake_append(self, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(BaseCheckpointService, "append_next_in_transaction", fake_append)

    service = WorkflowExecutionCheckpointService(None)
    await service.append_next_in_transaction(
        execution_id="execution",
        execution_status="running",
        state_data={},
        checkpoint_reason="node.completed",
        node_id="node",
        node_attempt=1,
        node_status="completed",
        expected_worker_owner="worker-1",
        expected_worker_attempt=7,
    )

    assert captured["expected_worker_owner"] == "worker-1"
    assert captured["expected_worker_attempt"] == 7
