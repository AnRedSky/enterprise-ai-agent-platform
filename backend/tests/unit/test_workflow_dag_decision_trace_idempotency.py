"""Unit coverage for idempotent durable DAG decision trace persistence."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


@pytest.mark.asyncio
async def test_record_dag_decision_requires_trace_identity():
    service = WorkflowRecoveryTraceLinkService(MagicMock())
    execution = MagicMock()
    execution.id = uuid4()
    execution.tenant_id = uuid4()
    execution.workflow_id = uuid4()
    execution.workflow_version_id = uuid4()

    result = await service.record_dag_decision(
        execution=execution,
        trace_id=None,
        actor_id=None,
        decision_id="decision-1",
        completed_node_ids=[],
        frontier_node_ids=["root"],
        selected_predecessors=[],
    )

    assert result is None


@pytest.mark.asyncio
async def test_record_dag_decision_is_idempotent_for_same_decision():
    db = MagicMock()
    db.execute = AsyncMock()
    existing = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = existing
    service = WorkflowRecoveryTraceLinkService(db)
    execution = MagicMock()
    execution.id = uuid4()
    execution.tenant_id = uuid4()
    execution.workflow_id = uuid4()
    execution.workflow_version_id = uuid4()
    execution.status = "running"

    result = await service.record_dag_decision(
        execution=execution,
        trace_id="trace-1",
        actor_id=None,
        decision_id="decision-1",
        completed_node_ids=["source"],
        frontier_node_ids=["target"],
        selected_predecessors=[{"node_id": "target", "predecessor_node_ids": ["source"]}],
    )

    assert result is existing
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_record_dag_decision_persists_new_decision_without_business_state():
    db = MagicMock()
    db.execute = AsyncMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    service = WorkflowRecoveryTraceLinkService(db)
    execution = MagicMock()
    execution.id = uuid4()
    execution.tenant_id = uuid4()
    execution.workflow_id = uuid4()
    execution.workflow_version_id = uuid4()
    execution.status = "running"

    await service.record_dag_decision(
        execution=execution,
        trace_id="trace-1",
        actor_id=None,
        decision_id="decision-1",
        completed_node_ids=["source"],
        frontier_node_ids=["target"],
        selected_predecessors=[{"node_id": "target", "predecessor_node_ids": ["source"]}],
    )

    event = db.add.call_args.args[0]
    assert event.data["decision_id"] == "decision-1"
    assert "state_data" not in event.data
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
