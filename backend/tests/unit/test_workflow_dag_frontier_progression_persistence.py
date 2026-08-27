"""DAG Frontier progression 持久化接线单元测试。

职责：验证 Planner 输出只能通过统一 complete_frontier_with_checkpoint Contract 持久化。
边界：不连接数据库，不执行 Worker，不验证真实 HTTP。
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.dag_frontier_progression import WorkflowDagFrontierProgressionService
from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlan


class _Frontier:
    def __init__(self) -> None:
        self.id = uuid4()
        self.execution_id = uuid4()
        self.workflow_version_id = uuid4()
        self.tenant_id = uuid4()
        self.frontier_key = "current"


@pytest.mark.asyncio
async def test_complete_frontier_delegates_persistence_to_atomic_contract(monkeypatch) -> None:
    frontier = _Frontier()
    current_plan = WorkflowDagResumeRuntimePlan(
        completed_node_ids=("root",),
        frontier_node_ids=("root",),
        nodes=({"id": "root", "type": "agent", "config": {}},),
        state_data={"value": 1},
        decision_fingerprint="current",
    )
    calls: list[dict] = []

    async def fake_complete(db, **kwargs):
        calls.append(kwargs)
        return "checkpoint", "next-frontier"

    monkeypatch.setattr(
        "app.services.workflow.checkpoint.recovery.dag_frontier_progression.complete_frontier_with_checkpoint",
        fake_complete,
    )

    result = await WorkflowDagFrontierProgressionService.complete_frontier(
        object(),
        frontier=frontier,
        worker_owner="worker-1",
        attempt=2,
        definition={
            "nodes": [
                {"id": "root", "type": "agent", "config": {}},
                {"id": "next", "type": "agent", "config": {}},
            ],
            "edges": [{"source": "root", "target": "next"}],
        },
        current_plan=current_plan,
        completed_node_ids={"root"},
        state_data_by_node={"root": {"value": 1}},
        checkpoint_state={"value": 1},
        checkpoint_reason="frontier_completed",
        now=datetime.now(timezone.utc),
    )

    assert result.checkpoint == "checkpoint"
    assert result.next_frontier == "next-frontier"
    assert calls[0]["frontier"] is frontier
    assert calls[0]["worker_owner"] == "worker-1"
    assert calls[0]["attempt"] == 2
    assert calls[0]["checkpoint_reason"] == "frontier_completed"
    assert calls[0]["next_identity"] is not None
    assert calls[0]["next_identity"].node_ids == ("next",)


@pytest.mark.asyncio
async def test_complete_frontier_does_not_persist_when_planning_rejects_incomplete_facts(monkeypatch) -> None:
    frontier = _Frontier()
    current_plan = WorkflowDagResumeRuntimePlan(
        completed_node_ids=("root",),
        frontier_node_ids=("root",),
        nodes=({"id": "root", "type": "agent", "config": {}},),
        state_data={"value": 1},
        decision_fingerprint="current",
    )
    called = False

    async def fake_complete(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(
        "app.services.workflow.checkpoint.recovery.dag_frontier_progression.complete_frontier_with_checkpoint",
        fake_complete,
    )

    with pytest.raises(ValueError, match="尚未全部形成 completed durable facts"):
        await WorkflowDagFrontierProgressionService.complete_frontier(
            object(),
            frontier=frontier,
            worker_owner="worker-1",
            attempt=1,
            definition={"nodes": [{"id": "root", "type": "agent", "config": {}}], "edges": []},
            current_plan=current_plan,
            completed_node_ids=set(),
            state_data_by_node={},
            checkpoint_state={"value": 1},
            checkpoint_reason="frontier_completed",
            now=datetime.now(timezone.utc),
        )

    assert called is False
