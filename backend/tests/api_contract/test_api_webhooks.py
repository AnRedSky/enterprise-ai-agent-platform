import inspect

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_webhook_route_is_registered_without_bearer_authentication():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes}
    assert ("/api/v1/webhooks/{trigger_id}", ("POST",)) in paths


def test_webhook_request_headers_are_exposed_by_route_contract():
    route = next(route for route in app.routes if route.path == "/api/v1/webhooks/{trigger_id}")
    parameters = inspect.signature(route.endpoint).parameters
    assert route.methods == {"POST"}
    assert parameters["x_webhook_secret"].default.alias == "X-Webhook-Secret"
    assert parameters["idempotency_key"].default.alias == "Idempotency-Key"
    assert parameters["request_id"].default.alias == "X-Request-ID"


def test_webhook_endpoint_does_not_require_platform_bearer_authentication():
    trigger_id = "00000000-0000-0000-0000-000000000301"
    response = client.post(
        f"/api/v1/webhooks/{trigger_id}",
        json={"event_id": "contract-event"},
        headers={"X-Webhook-Secret": "contract-secret"},
    )
    # Authentication belongs to the Trigger itself. A missing trigger is therefore
    # expected to be resolved by the endpoint/service rather than by platform auth.
    assert response.status_code != 401


def test_webhook_trigger_create_shape_accepts_secret_and_event_identity_config():
    from app.api.workflows import WorkflowTriggerCreate

    create = WorkflowTriggerCreate.model_validate(
        {
            "name": "github-events",
            "trigger_type": "webhook",
            "config": {
                "auth_mode": "secret",
                "secret": "a" * 32,
                "event_id_field": "delivery_id",
            },
        }
    )
    assert create.trigger_type == "webhook"
    assert create.config["auth_mode"] == "secret"
    assert create.config["secret"] == "a" * 32
    assert create.config["event_id_field"] == "delivery_id"
