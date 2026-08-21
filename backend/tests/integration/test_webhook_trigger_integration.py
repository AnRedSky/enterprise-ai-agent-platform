from uuid import UUID

from app.models.workflow_execution import WorkflowExecution
from app.services.webhook_trigger import WebhookTriggerService


def test_webhook_durable_idempotency_key_is_deterministic_and_fits_execution_schema():
    trigger_id = UUID("00000000-0000-0000-0000-000000000401")
    first = WebhookTriggerService.durable_idempotency_key(trigger_id, "event-123")
    second = WebhookTriggerService.durable_idempotency_key(trigger_id, "event-123")
    other = WebhookTriggerService.durable_idempotency_key(trigger_id, "event-456")

    assert first == second
    assert first != other
    assert first.startswith("webhook:")
    assert len(first) <= 100
    assert len(first) == len("webhook:") + 64


def test_workflow_execution_keeps_webhook_idempotency_as_the_durable_unique_boundary():
    constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in WorkflowExecution.__table__.constraints
        if constraint.name
    }
    assert constraints["uq_workflow_execution_tenant_idempotency"] == (
        "tenant_id",
        "idempotency_key",
    )
    assert WorkflowExecution.__table__.c.idempotency_key.type.length == 100
