"""Durable Frontier terminalization Contract 单元测试。

职责：只验证终态 Frontier progression 的领域约束，不启动数据库、Scheduler 或 Worker。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.workflow.frontier import WorkflowFrontierIdentity
from app.services.workflow.frontier_progression import (
    FrontierProgressionContractError,
    validate_frontier_progression_contract,
)


def test_terminal_frontier_requires_completed_execution() -> None:
    frontier = type("Frontier", (), {
        "execution_id": uuid4(),
        "workflow_version_id": uuid4(),
        "frontier_key": "frontier:current",
    })()

    with pytest.raises(FrontierProgressionContractError, match="必须进入 completed"):
        validate_frontier_progression_contract(
            frontier=frontier,
            next_identity=None,
            execution_status="running",
        )


def test_terminal_frontier_accepts_completed_execution_without_next_frontier() -> None:
    frontier = type("Frontier", (), {
        "execution_id": uuid4(),
        "workflow_version_id": uuid4(),
        "frontier_key": "frontier:current",
    })()

    validate_frontier_progression_contract(
        frontier=frontier,
        next_identity=None,
        execution_status="completed",
    )


def test_non_terminal_frontier_requires_same_execution_and_version() -> None:
    frontier = type("Frontier", (), {
        "execution_id": uuid4(),
        "workflow_version_id": uuid4(),
        "frontier_key": "frontier:current",
    })()
    next_identity = WorkflowFrontierIdentity(
        execution_id=uuid4(),
        workflow_version_id=frontier.workflow_version_id,
        decision_fingerprint="decision",
        node_ids=("node-next",),
    )

    with pytest.raises(FrontierProgressionContractError, match="同一个 Workflow Execution"):
        validate_frontier_progression_contract(
            frontier=frontier,
            next_identity=next_identity,
            execution_status="running",
        )
