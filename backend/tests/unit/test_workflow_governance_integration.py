from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.workflow.governance import WorkflowGovernanceService


@pytest.mark.asyncio
async def test_workflow_lifecycle_audit_publishes_durable_integration_event() -> None:
    db = MagicMock()
    db.flush = AsyncMock()
    execution = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
    )

    with patch(
        "app.services.workflow.governance.RuntimeIntegrationEventPublisher.publish",
        new_callable=AsyncMock,
    ) as publish:
        event = await WorkflowGovernanceService(db).audit(
            execution,
            execution.id,
            "workflow.execution.failed",
            "failed",
            error_code="RUNTIME_ERROR",
            metadata={"reason": "provider timeout"},
        )

    assert event.action == "workflow.execution.failed"
    publish.assert_awaited_once()
    kwargs = publish.await_args.kwargs
    assert kwargs["tenant_id"] == execution.tenant_id
    assert kwargs["event_type"] == "workflow.execution.failed"
    assert kwargs["source"] == "workflow-runtime"
    assert kwargs["subject"] == str(execution.id)
    assert kwargs["idempotency_key"] == f"workflow-execution:{execution.id}:audit:workflow.execution.failed"
    assert kwargs["payload"]["error_code"] == "RUNTIME_ERROR"
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_workflow_completion_audit_does_not_duplicate_frontier_integration_event() -> None:
    db = MagicMock()
    db.flush = AsyncMock()
    execution = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
    )

    with patch(
        "app.services.workflow.governance.RuntimeIntegrationEventPublisher.publish",
        new_callable=AsyncMock,
    ) as publish:
        event = await WorkflowGovernanceService(db).audit(
            execution,
            execution.id,
            "workflow.execution.completed",
            "success",
        )

    assert event.action == "workflow.execution.completed"
    publish.assert_not_awaited()
