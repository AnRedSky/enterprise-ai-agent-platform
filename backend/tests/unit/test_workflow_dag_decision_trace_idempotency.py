"""Durable DAG Decision Trace 幂等与 Replay 收敛测试。"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


def _execution():
    execution = MagicMock(); execution.id = uuid4(); execution.tenant_id = uuid4(); execution.workflow_id = uuid4(); execution.workflow_version_id = uuid4(); execution.status = "running"
    return execution


def _query_result(*rows):
    result = MagicMock(); result.scalars.return_value.all.return_value = list(rows); return result


@pytest.mark.asyncio
async def test_record_dag_decision_requires_trace_identity():
    service = WorkflowRecoveryTraceLinkService(MagicMock())
    result = await service.record_dag_decision(execution=_execution(), trace_id=None, actor_id=None, decision_id="decision-1", completed_node_ids=[], frontier_node_ids=["root"], selected_predecessors=[])
    assert result is None


@pytest.mark.asyncio
async def test_record_dag_decision_is_idempotent_for_same_decision():
    db = MagicMock(); db.execute = AsyncMock()
    first_result = _query_result(); second_result = MagicMock()
    existing = MagicMock(); existing.data = {"decision_id":"decision-1", "completed_node_ids":["source"], "frontier_node_ids":["target"], "selected_predecessors":[{"node_id":"target", "predecessor_node_ids":["source"]}]}
    second_result.scalar_one_or_none.return_value = existing; db.execute.side_effect = [first_result, second_result]
    service = WorkflowRecoveryTraceLinkService(db)
    result = await service.record_dag_decision(execution=_execution(), trace_id="trace-1", actor_id=None, decision_id="decision-1", completed_node_ids=["source"], frontier_node_ids=["target"], selected_predecessors=[{"node_id":"target", "predecessor_node_ids":["source"]}])
    assert result is existing; db.add.assert_not_called()


@pytest.mark.asyncio
async def test_record_dag_decision_rejects_existing_payload_drift():
    db = MagicMock(); db.execute = AsyncMock()
    existing = MagicMock(); existing.data = {"decision_id":"decision-1", "completed_node_ids":["source"], "frontier_node_ids":["wrong-target"], "selected_predecessors":[]}
    lookup_result = MagicMock(); lookup_result.scalar_one_or_none.return_value = existing
    db.execute.side_effect = [_query_result(existing.data), lookup_result]
    service = WorkflowRecoveryTraceLinkService(db)
    with pytest.raises(ValueError, match="frontier 不一致"):
        await service.record_dag_decision(execution=_execution(), trace_id="trace-1", actor_id=None, decision_id="decision-1", completed_node_ids=["source"], frontier_node_ids=["target"], selected_predecessors=[])
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_record_dag_decision_persists_new_decision_without_business_state():
    db = MagicMock(); db.execute = AsyncMock()
    first_result = _query_result(); second_result = MagicMock(); second_result.scalar_one_or_none.return_value = None
    db.execute.side_effect = [first_result, second_result]
    db.flush = AsyncMock(); db.commit = AsyncMock(); db.refresh = AsyncMock()
    service = WorkflowRecoveryTraceLinkService(db); execution = _execution()
    await service.record_dag_decision(execution=execution, trace_id="trace-1", actor_id=None, decision_id="decision-1", completed_node_ids=["source"], frontier_node_ids=["target"], selected_predecessors=[{"node_id":"target", "predecessor_node_ids":["source"]}])
    event = db.add.call_args.args[0]
    assert event.data["decision_id"] == "decision-1"; assert "state_data" not in event.data
    db.flush.assert_awaited_once(); db.commit.assert_awaited_once()
