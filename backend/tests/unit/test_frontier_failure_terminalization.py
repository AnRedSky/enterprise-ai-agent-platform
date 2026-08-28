from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow_worker.durable_frontier_execution import PlannerDrivenDurableFrontierWorkflowWorker


@pytest.mark.asyncio
async def test_failure_terminalization_closes_active_sibling_frontiers() -> None:
    db = AsyncMock()
    execution = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), status="running", created_by=uuid4())
    worker = object.__new__(PlannerDrivenDurableFrontierWorkflowWorker)

    await worker._mark_active_sibling_frontiers_failed(
        db,
        execution,
        now=SimpleNamespace(),
        error_code="WORKFLOW_EXECUTION_FAILED",
        error_message="node failed",
    )

    db.execute.assert_awaited_once()
    statement = db.execute.await_args.args[0]
    compiled = statement.compile()
    assert "workflow_frontiers" in str(statement)
    assert compiled.params["status"] == "failed"
    assert compiled.params["error_code"] == "WORKFLOW_EXECUTION_FAILED"
    assert compiled.params["error_message"] == "node failed"


@pytest.mark.asyncio
async def test_failed_execution_repeated_failure_keeps_siblings_terminal() -> None:
    db = AsyncMock()
    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), status="failed", created_by=uuid4()
    )
    worker = object.__new__(PlannerDrivenDurableFrontierWorkflowWorker)
    worker._mark_active_sibling_frontiers_failed = AsyncMock()
    now = SimpleNamespace()

    await worker._mark_execution_failed_in_transaction(
        db,
        execution,
        now=now,
        error_code="WORKFLOW_EXECUTION_FAILED",
        error_message="duplicate failure",
    )

    worker._mark_active_sibling_frontiers_failed.assert_awaited_once_with(
        db,
        execution,
        now=now,
        error_code="WORKFLOW_EXECUTION_FAILED",
        error_message="duplicate failure",
    )
