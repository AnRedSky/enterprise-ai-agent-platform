"""Workflow Trigger Service 单元测试：验证 Manual Invoke 的事务提交边界。

职责：锁定 commit=False 必须一路传递到 WorkflowExecutionService.run 的事务契约。
边界：不访问 PostgreSQL，不启动 API、Worker、Scheduler 或 Redis。
关键依赖：WorkflowTriggerService、WorkflowExecutionService 的可控替身。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.trigger.service import WorkflowTriggerService


@pytest.mark.asyncio
async def test_manual_invoke_forwards_commit_boundary_to_execution_run(monkeypatch) -> None:
    """验证 Operator Governance 使用 commit=False 时，Execution Runtime 不能自行提前提交。"""
    execute_result = SimpleNamespace(scalar_one_or_none=lambda: None)
    db = SimpleNamespace(commit=AsyncMock(), execute=AsyncMock(return_value=execute_result))
    service = WorkflowTriggerService(db)
    workflow = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        status="published",
        published_version_id=uuid4(),
    )
    trigger = SimpleNamespace(
        id=uuid4(),
        tenant_id=workflow.tenant_id,
        workflow_id=workflow.id,
        status="enabled",
        trigger_type="manual",
    )
    version = SimpleNamespace(id=workflow.published_version_id, status="published")
    execution = SimpleNamespace(id=uuid4())
    run = AsyncMock(return_value=execution)
    create = AsyncMock(return_value=execution)
    fake_execution_service = SimpleNamespace(create=create, run=run)

    async def fake_get_published_version(_workflow):
        return version

    monkeypatch.setattr(service, "_get_published_version", fake_get_published_version)
    monkeypatch.setattr(
        "app.services.trigger.service.WorkflowExecutionService",
        lambda _db: fake_execution_service,
    )
    service.governance.audit = AsyncMock()
    service.governance.trace = AsyncMock()

    result = await service.invoke(
        workflow,
        trigger,
        uuid4(),
        {"source": "operator"},
        idempotency_key=f"operator-trigger-{uuid4()}",
        is_admin=True,
        commit=False,
    )

    assert result is execution
    create.assert_awaited_once()
    assert create.await_args.kwargs["commit"] is False
    run.assert_awaited_once()
    assert run.await_args.kwargs["commit"] is False
    db.commit.assert_not_awaited()
