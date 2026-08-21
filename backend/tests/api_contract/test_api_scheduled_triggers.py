from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_scheduled_trigger_routes_share_existing_workflow_trigger_contract():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/workflows/{workflow_id}/triggers")}
    assert ("/api/v1/workflows/{workflow_id}/triggers", ("POST",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}", ("GET",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}", ("PATCH",)) in paths
    assert ("/api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke", ("POST",)) in paths


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


def test_scheduled_trigger_request_shape_is_documented_by_route_payload_contract():
    from app.api.workflows import WorkflowTriggerCreate, WorkflowTriggerUpdate

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
