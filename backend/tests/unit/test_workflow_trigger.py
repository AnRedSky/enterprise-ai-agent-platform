"""验证 Trigger 生命周期服务的类型、状态、创建和调用边界。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.trigger import WorkflowTriggerService


def _service():
    db = SimpleNamespace()
    db.execute = AsyncMock()
    db.add = lambda *_args, **_kwargs: None
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return WorkflowTriggerService(db), db


def test_trigger_type_contract_only_allows_manual():
    assert WorkflowTriggerService.validate_type("manual") == "manual"
    with pytest.raises(HTTPException) as exc:
        WorkflowTriggerService.validate_type("cron")
    assert exc.value.status_code == 422


def test_trigger_status_contract():
    assert WorkflowTriggerService.validate_status("enabled") == "enabled"
    assert WorkflowTriggerService.validate_status("disabled") == "disabled"
    with pytest.raises(HTTPException) as exc:
        WorkflowTriggerService.validate_status("paused")
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_create_trigger_defaults_to_enabled_manual():
    service, db = _service()
    trigger = await service.create(SimpleNamespace(id=uuid4(), tenant_id=uuid4(), status="published"), uuid4(), "api", "manual", {})
    assert trigger.status == "enabled"
    assert trigger.trigger_type == "manual"
    assert trigger.name == "api"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_invoke_rejects_disabled_trigger_before_execution():
    service, _db = _service()
    workflow = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), status="published", published_version_id=uuid4())
    trigger = SimpleNamespace(status="disabled", trigger_type="manual", id=uuid4())
    with pytest.raises(HTTPException) as exc:
        await service.invoke(workflow, trigger, uuid4(), {}, idempotency_key="disabled-1")
    assert exc.value.status_code == 409
    assert "禁用" in exc.value.detail


@pytest.mark.asyncio
async def test_invoke_rejects_unpublished_workflow():
    service, _db = _service()
    workflow = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), status="draft", published_version_id=None)
    trigger = SimpleNamespace(status="enabled", trigger_type="manual", id=uuid4())
    with pytest.raises(HTTPException) as exc:
        await service.invoke(workflow, trigger, uuid4(), {})
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_invoke_rejects_non_manual_trigger():
    service, _db = _service()
    workflow = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), status="published", published_version_id=uuid4())
    trigger = SimpleNamespace(status="enabled", trigger_type="cron", id=uuid4())
    with pytest.raises(HTTPException) as exc:
        await service.invoke(workflow, trigger, uuid4(), {})
    assert exc.value.status_code == 409
