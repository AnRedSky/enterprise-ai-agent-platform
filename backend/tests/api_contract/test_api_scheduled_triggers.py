"""定时 Trigger API Contract 测试。

职责：验证 Workflow Trigger 路由、Scheduler 状态查询、认证要求及请求模型契约。
边界：只验证 HTTP Contract 与 Pydantic 请求模型，不实现 Trigger 或 Scheduler 业务逻辑。
关键依赖：FastAPI TestClient 与 Workflow v1 API Router。
"""

from fastapi.testclient import TestClient

from app.api.v1.workflows.router import WorkflowTriggerCreate, WorkflowTriggerUpdate
from app.main import app

client = TestClient(app)


def test_scheduled_trigger_routes_share_existing_workflow_trigger_contract():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/workflows/{workflow_id}/triggers")}
    assert ("/api/v1/workflows/{workflow_id}/triggers", ("POST",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}", ("GET",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}", ("PATCH",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke", ("POST",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}/schedule", ("GET",)) in paths


def test_scheduled_trigger_create_requires_bearer_authentication():
    workflow_id = "00000000-0000-0000-0000-000000000201"
    response = client.post(
        f"/api/v1/workflows/{workflow_id}/triggers",
        json={
            "name": "scheduled-contract",
            "trigger_type": "scheduled",
            "config": {"timezone": "Asia/Shanghai", "interval_seconds": 300},
        },
    )
    assert response.status_code == 401


def test_scheduled_trigger_update_requires_bearer_authentication():
    workflow_id = "00000000-0000-0000-0000-000000000201"
    trigger_id = "00000000-0000-0000-0000-000000000202"
    response = client.patch(
        f"/api/v1/workflows/{workflow_id}/triggers/{trigger_id}",
        json={"config": {"timezone": "UTC", "interval_seconds": 600}},
    )
    assert response.status_code == 401


def test_scheduled_trigger_invoke_requires_bearer_authentication():
    workflow_id = "00000000-0000-0000-0000-000000000201"
    trigger_id = "00000000-0000-0000-0000-000000000202"
    response = client.post(f"/api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke", json={})
    assert response.status_code == 401


def test_scheduled_trigger_status_requires_bearer_authentication():
    workflow_id = "00000000-0000-0000-0000-000000000201"
    trigger_id = "00000000-0000-0000-0000-000000000202"
    response = client.get(f"/api/v1/workflows/{workflow_id}/triggers/{trigger_id}/schedule")
    assert response.status_code == 401


def test_scheduled_trigger_request_shape_is_documented_by_route_payload_contract():
    create = WorkflowTriggerCreate.model_validate({
        "name": "nightly",
        "trigger_type": "scheduled",
        "config": {"timezone": "Asia/Shanghai", "interval_seconds": 300},
    })
    assert create.trigger_type == "scheduled"
    assert create.config == {"timezone": "Asia/Shanghai", "interval_seconds": 300}

    update = WorkflowTriggerUpdate.model_validate({
        "config": {"timezone": "UTC", "interval_seconds": 600},
    })
    assert update.config == {"timezone": "UTC", "interval_seconds": 600}
