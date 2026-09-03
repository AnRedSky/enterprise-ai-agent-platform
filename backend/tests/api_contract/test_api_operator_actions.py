"""Operator Action API Contract 测试。

职责：验证 Operator Action HTTP 路由、鉴权、请求头传递和领域 HTTPException 的协议边界。
边界：不启动 API、Scheduler、Worker、PostgreSQL 或 Redis；业务幂等并发语义由 integration 层验证。
关键依赖：FastAPI ASGITransport、JWT 鉴权依赖与 OperatorActionGovernanceService。
"""

from inspect import signature
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.v1.runtime import operator_actions
from app.core.security import create_token
from app.dependencies.db import get_db
from app.main import app
from app.services.trigger import WorkflowTriggerService


class FakeDB:
    """提供本 Contract 测试所需的最小数据库依赖，不模拟领域算法。"""

    async def rollback(self):
        pass


@pytest.fixture
def db_override():
    """注入最小数据库替身，并在测试结束后恢复全局依赖覆盖。"""
    db = FakeDB()

    async def override():
        yield db

    app.dependency_overrides[get_db] = override
    yield db
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def auth_headers():
    """生成仅用于 Contract 测试的租户用户 Token，无需人工填写身份数据。"""
    tenant_id = uuid4()
    actor_id = uuid4()
    return {"Authorization": f"Bearer {create_token(actor_id, [\"user\"], tenant_id=tenant_id)}"}


def test_operator_action_routes_are_registered():
    paths = {route.path for route in operator_actions.router.routes}
    assert "/api/v1/runtime/operator-actions/workflow-executions/{execution_id}" in paths
    assert "/api/v1/runtime/operator-actions/workflow-executions/{execution_id}/{action}" in paths
    assert "/api/v1/runtime/operator-actions/workflow-triggers/{trigger_id}" in paths
    assert "/api/v1/runtime/operator-actions/workflow-triggers/{trigger_id}/{action}" in paths


def test_operator_action_request_has_explicit_confirmation_and_payload_defaults():
    request = operator_actions.OperatorActionRequest()
    assert request.confirm is False
    assert request.reason is None
    assert request.input_data == {}


def test_manual_trigger_invoke_exposes_deferred_commit_boundary():
    """验证 Operator Governance 可以让 Manual Trigger 延迟提交到统一治理事务。"""
    parameter = signature(WorkflowTriggerService.invoke).parameters["commit"]
    assert parameter.kind is parameter.KEYWORD_ONLY
    assert parameter.default is True


@pytest.mark.asyncio
async def test_operator_action_routes_require_bearer_authentication():
    execution_id = uuid4()
    trigger_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        execution_availability = await client.get(
            f"/api/v1/runtime/operator-actions/workflow-executions/{execution_id}"
        )
        execution_action = await client.post(
            f"/api/v1/runtime/operator-actions/workflow-executions/{execution_id}/retry",
            json={"confirm": True},
        )
        trigger_availability = await client.get(
            f"/api/v1/runtime/operator-actions/workflow-triggers/{trigger_id}"
        )
        trigger_action = await client.post(
            f"/api/v1/runtime/operator-actions/workflow-triggers/{trigger_id}/invoke",
            headers={"Idempotency-Key": "contract-auth-check"},
            json={},
        )

    assert execution_availability.status_code == 401
    assert execution_action.status_code == 401
    assert trigger_availability.status_code == 401
    assert trigger_action.status_code == 401


@pytest.mark.asyncio
async def test_trigger_invoke_forwards_idempotency_key_to_governance(db_override, auth_headers, monkeypatch):
    """验证 HTTP Contract 不丢失 Idempotency-Key，并保持统一治理服务的响应结构。"""
    trigger_id = uuid4()
    workflow_id = uuid4()
    execution_id = uuid4()
    captured = {}

    class FakeGovernance:
        def __init__(self, db):
            assert db is db_override

        async def execute_trigger(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                id=execution_id,
                tenant_id=args[1],
                workflow_id=workflow_id,
                workflow_version_id=uuid4(),
                created_by=args[2],
                retry_of_execution_id=None,
                resume_of_execution_id=None,
                resume_checkpoint_sequence=None,
                idempotency_key="operator-contract-key",
                status="succeeded",
                current_node_id=None,
                input_data={"prompt": "contract"},
                output_data={"ok": True},
                error_code=None,
                error_message=None,
                started_at=None,
                ended_at=None,
                created_at=None,
            )

    monkeypatch.setattr(operator_actions, "OperatorActionGovernanceService", FakeGovernance)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/runtime/operator-actions/workflow-triggers/{trigger_id}/invoke",
            headers={**auth_headers, "Idempotency-Key": "operator-contract-key"},
            json={"input_data": {"prompt": "contract"}},
        )

    assert response.status_code == 200
    assert captured["args"][0] == trigger_id
    assert captured["args"][4] == "invoke"
    assert captured["kwargs"]["idempotency_key"] == "operator-contract-key"
    assert response.json()["resource_type"] == "workflow_execution"
    assert response.json()["result"]["id"] == str(execution_id)


@pytest.mark.asyncio
async def test_operator_action_http_exception_is_preserved(db_override, auth_headers, monkeypatch):
    """验证治理层的 409 冲突不会被 API 层错误转换为 500。"""
    trigger_id = uuid4()

    class FakeGovernance:
        def __init__(self, db):
            assert db is db_override

        async def execute_trigger(self, *args, **kwargs):
            raise HTTPException(status_code=409, detail="Idempotency-Key 已用于其他 Operator Action")

    monkeypatch.setattr(operator_actions, "OperatorActionGovernanceService", FakeGovernance)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/runtime/operator-actions/workflow-triggers/{trigger_id}/invoke",
            headers={**auth_headers, "Idempotency-Key": "operator-conflict-key"},
            json={"input_data": {}},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Idempotency-Key 已用于其他 Operator Action"
