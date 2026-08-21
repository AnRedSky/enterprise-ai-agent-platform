from uuid import UUID

from app.services.webhook_trigger import WebhookTriggerService


TRIGGER_ID = UUID("d4d5337b-51d3-4d08-90eb-128c0a6372a4")


def test_durable_idempotency_key_preserves_public_identity_when_bounded():
    identity = "event-0cb4e80ff85c"

    key = WebhookTriggerService.durable_idempotency_key(TRIGGER_ID, identity)

    assert key == f"webhook:{TRIGGER_ID}:{identity}"
    assert len(key) <= 100


def test_durable_idempotency_key_falls_back_to_digest_when_public_key_is_too_long():
    identity = "x" * 100

    key = WebhookTriggerService.durable_idempotency_key(TRIGGER_ID, identity)

    assert key.startswith("webhook:")
    assert key != f"webhook:{TRIGGER_ID}:{identity}"
    assert len(key) <= 100
    assert key == WebhookTriggerService.durable_idempotency_key(TRIGGER_ID, identity)
