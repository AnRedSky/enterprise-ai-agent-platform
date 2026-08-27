"""Recovery Trace Link 单元测试。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value or []


@pytest.mark.asyncio
async def test_trace_link_stores_checkpoint_lineage_without_runtime_state():
    db = AsyncMock()
    checkpoint_sequence = 7
    checkpoint_result = _ScalarResult(checkpoint_sequence)
    existing_result = _ScalarResult(None)
    db.execute.side_effect = [checkpoint_result, existing_result]
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = lambda event: None

    source = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    resume = SimpleNamespace(
        id=uuid4(), tenant_id=source.tenant_id, workflow_id=uuid4(),
        workflow_version_id=uuid4(), resume_of_execution_id=source.id,
        resume_checkpoint_sequence=checkpoint_sequence, status="pending",
    )

    service = WorkflowRecoveryTraceLinkService(db)
    event = await service.link(source, resume, "trace-123", uuid4())

    assert event.execution_id == resume.id
    assert event.trace_id == "trace-123"
    assert event.event_type == service.EVENT_TYPE
    assert event.data == {
        "source_execution_id": str(source.id),
        "resume_execution_id": str(resume.id),
        "resume_checkpoint_sequence": checkpoint_sequence,
        "phase": "automatic_recovery",
    }
    assert "state_data" not in event.data
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_trace_link_can_defer_commit_to_outer_recovery_transaction():
    db = AsyncMock()
    db.execute.side_effect = [_ScalarResult(8), _ScalarResult(None)]
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = lambda event: None

    source = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    resume = SimpleNamespace(
        id=uuid4(), tenant_id=source.tenant_id, workflow_id=uuid4(),
        workflow_version_id=uuid4(), resume_of_execution_id=source.id,
        resume_checkpoint_sequence=8, status="pending",
    )

    event = await WorkflowRecoveryTraceLinkService(db).link(
        source, resume, "trace-outer", uuid4(), commit=False
    )

    assert event.data["resume_checkpoint_sequence"] == 8
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_trace_link_returns_existing_event_without_duplicate_write():
    db = AsyncMock()
    existing = SimpleNamespace(
        id=uuid4(), trace_id="trace-existing",
        data={
            "source_execution_id": "source",
            "resume_execution_id": "resume",
            "resume_checkpoint_sequence": 9,
        },
    )
    db.execute.side_effect = [_ScalarResult(9), _ScalarResult(existing)]

    source = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    resume = SimpleNamespace(
        id=uuid4(), tenant_id=source.tenant_id, workflow_id=uuid4(),
        workflow_version_id=uuid4(), resume_of_execution_id=source.id,
        resume_checkpoint_sequence=9, status="pending",
    )
    existing.data["source_execution_id"] = str(source.id)
    existing.data["resume_execution_id"] = str(resume.id)

    result = await WorkflowRecoveryTraceLinkService(db).link(
        source, resume, "trace-existing", uuid4()
    )

    assert result is existing
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_dag_decision_can_defer_commit_to_outer_transaction():
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(None)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = lambda event: None

    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), status="running"
    )
    service = WorkflowRecoveryTraceLinkService(db)

    event = await service.record_dag_decision(
        execution,
        "trace-1",
        uuid4(),
        "fingerprint-1",
        ["a"],
        ["b"],
        [{"node_id": "b", "predecessor_node_ids": ["a"]}],
        commit=False,
    )

    assert event is not None
    assert event.data["decision_id"] == "fingerprint-1"
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_dag_decision_defaults_to_compatibility_commit():
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(None)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = lambda event: None

    execution = SimpleNamespace(
        id=uuid4(), tenant_id=uuid4(), workflow_id=uuid4(), workflow_version_id=uuid4(), status="running"
    )

    await WorkflowRecoveryTraceLinkService(db).record_dag_decision(
        execution, "trace-2", uuid4(), "fingerprint-2", ["a"], ["b"], []
    )

    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()
