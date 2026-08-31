"""批量 Operator Action 单元测试。

职责：验证批量请求约束、去重边界、单项委托和逐项结果聚合。
边界：不启动服务、不访问真实数据库，不复制 Workflow / Trigger 生命周期。
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.runtime_operations.batch_operator_actions import BatchOperatorActionService


def test_batch_request_rejects_duplicate_resource_ids():
    first = uuid4()
    with pytest.raises(HTTPException) as exc_info:
        BatchOperatorActionService.validate_request(
            "workflow_execution", "cancel", [first, first], confirm=True, idempotency_key=None,
        )
    assert exc_info.value.status_code == 422


def test_batch_request_rejects_more_than_100_resources():
    with pytest.raises(HTTPException) as exc_info:
        BatchOperatorActionService.validate_request(
            "workflow_execution", "cancel", [uuid4() for _ in range(101)], confirm=True, idempotency_key=None,
        )
    assert exc_info.value.status_code == 422


def test_batch_retry_requires_batch_idempotency_key():
    with pytest.raises(HTTPException) as exc_info:
        BatchOperatorActionService.validate_request(
            "workflow_execution", "retry", [uuid4()], confirm=True, idempotency_key=None,
        )
    assert exc_info.value.status_code == 400


def test_batch_item_idempotency_key_is_stable_and_bounded():
    key = BatchOperatorActionService._item_idempotency_key(
        "operator-batch", "workflow_execution", "retry", uuid4(),
    )
    assert key.startswith("batch-")
    assert len(key) == 70


@pytest.mark.asyncio
async def test_batch_execution_delegates_each_item_to_existing_governance_service():
    db = AsyncMock()
    service = BatchOperatorActionService(db)
    service.operator.execute_execution = AsyncMock(side_effect=lambda resource_id, *_args, **_kwargs: type(
        "Result", (), {"id": resource_id, "status": "cancelled"}
    )())
    ids = [uuid4(), uuid4()]

    result = await service.execute(
        resource_type="workflow_execution",
        action="cancel",
        resource_ids=ids,
        tenant_id=uuid4(),
        actor_id=uuid4(),
        is_admin=True,
        confirm=True,
    )

    assert result["total"] == 2
    assert result["succeeded_count"] == 2
    assert result["rejected_count"] == 0
    assert result["failed_count"] == 0
    assert [item.resource_id for item in result["items"]] == ids
    assert service.operator.execute_execution.await_count == 2


@pytest.mark.asyncio
async def test_batch_execution_keeps_rejected_items_and_continues():
    db = AsyncMock()
    service = BatchOperatorActionService(db)
    first, second = uuid4(), uuid4()

    async def execute(resource_id, *_args, **_kwargs):
        if resource_id == first:
            raise HTTPException(status_code=409, detail="当前状态不允许")
        return type("Result", (), {"id": resource_id, "status": "cancelled"})()

    service.operator.execute_execution = AsyncMock(side_effect=execute)
    result = await service.execute(
        resource_type="workflow_execution",
        action="cancel",
        resource_ids=[first, second],
        tenant_id=uuid4(),
        actor_id=uuid4(),
        is_admin=True,
        confirm=True,
    )

    assert result["succeeded_count"] == 1
    assert result["rejected_count"] == 1
    assert result["items"][0].error_code == "HTTP_409"
    assert result["items"][1].status == "succeeded"


def test_batch_item_idempotency_key_differs_by_resource():
    resource_a, resource_b = uuid4(), uuid4()
    key_a = BatchOperatorActionService._item_idempotency_key("batch", "workflow_execution", "retry", resource_a)
    key_b = BatchOperatorActionService._item_idempotency_key("batch", "workflow_execution", "retry", resource_b)
    assert key_a != key_b
