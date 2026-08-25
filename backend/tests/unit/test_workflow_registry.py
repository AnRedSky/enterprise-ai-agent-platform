from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.workflow import WorkflowRegistry


@pytest.mark.asyncio
async def test_publish_rejects_invalid_workflow_definition_before_state_change():
    """发布边界必须拒绝不可执行定义，避免坏版本进入 published 状态。"""
    db = AsyncMock()
    registry = WorkflowRegistry(db)
    workflow = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        status="draft",
        published_version_id=None,
    )
    version = SimpleNamespace(
        id=uuid4(),
        workflow_id=workflow.id,
        version="1.0.0",
        status="draft",
        definition={"nodes": []},
    )

    with pytest.raises(HTTPException) as exc:
        await registry.publish(workflow, version, uuid4())

    assert exc.value.status_code == 422
    assert exc.value.detail == "Workflow definition 必须包含非空 nodes"
    assert workflow.status == "draft"
    assert workflow.published_version_id is None
    assert version.status == "draft"
    db.commit.assert_not_awaited()
