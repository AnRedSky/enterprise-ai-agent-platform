"""Unit contract for Recovery trace → Resume checkpoint lineage."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Db:
    def __init__(self, value):
        self.value = value

    async def execute(self, _query):
        return _ScalarResult(self.value)


@pytest.mark.asyncio
async def test_resume_checkpoint_lineage_requires_source_relationship():
    source = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4())
    resume = SimpleNamespace(
        id=uuid4(),
        tenant_id=source.tenant_id,
        workflow_version_id=source.workflow_version_id,
        resume_of_execution_id=uuid4(),
        resume_checkpoint_sequence=3,
    )
    service = WorkflowRecoveryTraceLinkService(_Db(3))

    with pytest.raises(ValueError, match="必须指向 Source Execution"):
        await service._assert_resume_checkpoint_lineage(source, resume)


@pytest.mark.asyncio
async def test_resume_checkpoint_lineage_requires_existing_checkpoint():
    source = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4())
    resume = SimpleNamespace(
        id=uuid4(),
        tenant_id=source.tenant_id,
        workflow_version_id=source.workflow_version_id,
        resume_of_execution_id=source.id,
        resume_checkpoint_sequence=3,
    )
    service = WorkflowRecoveryTraceLinkService(_Db(None))

    with pytest.raises(ValueError, match="resume_checkpoint_sequence 不存在"):
        await service._assert_resume_checkpoint_lineage(source, resume)


@pytest.mark.asyncio
async def test_resume_checkpoint_lineage_accepts_matching_durable_checkpoint():
    source = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), workflow_version_id=uuid4())
    resume = SimpleNamespace(
        id=uuid4(),
        tenant_id=source.tenant_id,
        workflow_version_id=source.workflow_version_id,
        resume_of_execution_id=source.id,
        resume_checkpoint_sequence=3,
    )
    service = WorkflowRecoveryTraceLinkService(_Db(3))

    assert await service._assert_resume_checkpoint_lineage(source, resume) == 3
