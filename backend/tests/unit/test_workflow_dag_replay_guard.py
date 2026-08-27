from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


@pytest.mark.asyncio
async def test_replay_guard_accepts_same_fingerprint_for_same_completed_facts():
    execution = SimpleNamespace(tenant_id="tenant-1", workflow_version_id="version-1")
    db = SimpleNamespace()
    db.execute = AsyncMock(
        return_value=SimpleNamespace(
            scalars=lambda: SimpleNamespace(
                all=lambda: [
                    {
                        "decision_id": "fingerprint-1",
                        "completed_node_ids": ["node-a"],
                        "frontier_node_ids": ["node-b"],
                        "selected_predecessors": [
                            {"node_id": "node-b", "predecessor_node_ids": ["node-a"]}
                        ],
                    }
                ]
            )
        )
    )

    service = WorkflowRecoveryTraceLinkService(db)
    await service.assert_dag_decision_replay_consistent(
        execution,
        "trace-1",
        ["node-a"],
        "fingerprint-1",
        ["node-b"],
        [{"node_id": "node-b", "predecessor_node_ids": ["node-a"]}],
    )


@pytest.mark.asyncio
async def test_replay_guard_rejects_changed_fingerprint_for_same_completed_facts():
    execution = SimpleNamespace(tenant_id="tenant-1", workflow_version_id="version-1")
    db = SimpleNamespace()
    db.execute = AsyncMock(
        return_value=SimpleNamespace(
            scalars=lambda: SimpleNamespace(
                all=lambda: [
                    {
                        "decision_id": "fingerprint-old",
                        "completed_node_ids": ["node-a"],
                    }
                ]
            )
        )
    )

    service = WorkflowRecoveryTraceLinkService(db)
    with pytest.raises(ValueError, match="Decision fingerprint 不一致"):
        await service.assert_dag_decision_replay_consistent(
            execution,
            "trace-1",
            ["node-a"],
            "fingerprint-new",
        )


@pytest.mark.asyncio
async def test_replay_guard_rejects_changed_frontier_for_same_completed_facts():
    execution = SimpleNamespace(tenant_id="tenant-1", workflow_version_id="version-1")
    db = SimpleNamespace()
    db.execute = AsyncMock(
        return_value=SimpleNamespace(
            scalars=lambda: SimpleNamespace(
                all=lambda: [
                    {
                        "decision_id": "fingerprint-1",
                        "completed_node_ids": ["node-a"],
                        "frontier_node_ids": ["node-b"],
                        "selected_predecessors": [
                            {"node_id": "node-b", "predecessor_node_ids": ["node-a"]}
                        ],
                    }
                ]
            )
        )
    )

    service = WorkflowRecoveryTraceLinkService(db)
    with pytest.raises(ValueError, match="frontier 不一致"):
        await service.assert_dag_decision_replay_consistent(
            execution,
            "trace-1",
            ["node-a"],
            "fingerprint-1",
            ["node-c"],
            [{"node_id": "node-c", "predecessor_node_ids": ["node-a"]}],
        )


@pytest.mark.asyncio
async def test_replay_guard_rejects_changed_predecessor_selection_for_same_completed_facts():
    execution = SimpleNamespace(tenant_id="tenant-1", workflow_version_id="version-1")
    db = SimpleNamespace()
    db.execute = AsyncMock(
        return_value=SimpleNamespace(
            scalars=lambda: SimpleNamespace(
                all=lambda: [
                    {
                        "decision_id": "fingerprint-1",
                        "completed_node_ids": ["node-a"],
                        "frontier_node_ids": ["node-b"],
                        "selected_predecessors": [
                            {"node_id": "node-b", "predecessor_node_ids": ["node-a"]}
                        ],
                    }
                ]
            )
        )
    )

    service = WorkflowRecoveryTraceLinkService(db)
    with pytest.raises(ValueError, match="predecessor 不一致"):
        await service.assert_dag_decision_replay_consistent(
            execution,
            "trace-1",
            ["node-a"],
            "fingerprint-1",
            ["node-b"],
            [{"node_id": "node-b", "predecessor_node_ids": ["node-x"]}],
        )
