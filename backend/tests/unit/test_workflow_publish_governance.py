from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.workflow import Workflow, WorkflowVersion
from app.services.workflow import WorkflowRegistry


def _result(value):
    result = MagicMock(); result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_publish_sets_active_version_and_is_idempotent():
    db = MagicMock(); db.execute = AsyncMock(return_value=_result(None)); db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()
    workflow_id = uuid4(); version_id = uuid4(); actor_id = uuid4()
    workflow = Workflow(id=workflow_id, owner_id=actor_id, name="demo", status="draft")
    version = WorkflowVersion(id=version_id, workflow_id=workflow_id, version="1.0.0", definition={"nodes": []}, status="draft", created_by=actor_id)
    registry = WorkflowRegistry(db)
    published = await registry.publish(workflow, version, actor_id)
    assert published is version; assert version.status == "published"; assert workflow.status == "published"; assert workflow.published_version_id == version_id
    assert db.commit.await_count == 1; assert db.add.call_count == 1
    published_again = await registry.publish(workflow, version, actor_id)
    assert published_again is version; assert db.commit.await_count == 1; assert db.add.call_count == 1


@pytest.mark.asyncio
async def test_publish_deprecates_previous_active_version():
    db = MagicMock(); previous_id = uuid4(); db.execute = AsyncMock(return_value=_result(None)); db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()
    workflow_id = uuid4(); actor_id = uuid4()
    workflow = Workflow(id=workflow_id, owner_id=actor_id, name="demo", status="published", published_version_id=previous_id)
    previous = WorkflowVersion(id=previous_id, workflow_id=workflow_id, version="1.0.0", definition={"nodes": []}, status="published", created_by=actor_id)
    current = WorkflowVersion(id=uuid4(), workflow_id=workflow_id, version="1.1.0", definition={"nodes": ["new"]}, status="testing", created_by=actor_id)
    db.execute.return_value = _result(previous)
    published = await WorkflowRegistry(db).publish(workflow, current, actor_id)
    assert published is current; assert previous.status == "deprecated"; assert current.status == "published"; assert workflow.published_version_id == current.id; assert workflow.status == "published"


@pytest.mark.asyncio
async def test_publish_rejects_archived_version():
    db = MagicMock(); db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()
    workflow = Workflow(id=uuid4(), owner_id=uuid4(), name="demo", status="draft")
    version = WorkflowVersion(id=uuid4(), workflow_id=workflow.id, version="1.0.0", definition={}, status="archived", created_by=workflow.owner_id)
    with pytest.raises(Exception, match="当前版本状态不允许发布"):
        await WorkflowRegistry(db).publish(workflow, version, workflow.owner_id)
