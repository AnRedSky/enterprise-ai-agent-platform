from app.models.registry import WebhookDelivery, WebhookDestination, WebhookSubscription


def test_webhook_models_are_registered_with_expected_tables() -> None:
    assert WebhookDestination.__tablename__ == "webhook_destinations"
    assert WebhookSubscription.__tablename__ == "webhook_subscriptions"
    assert WebhookDelivery.__tablename__ == "webhook_deliveries"


def test_webhook_subscription_and_delivery_preserve_destination_fanout_boundary() -> None:
    assert "destination_id" in WebhookSubscription.__table__.c
    assert "destination_id" in WebhookDelivery.__table__.c
    assert "integration_event_id" in WebhookDelivery.__table__.c
