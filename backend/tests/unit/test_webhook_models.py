from app.models.registry import WebhookDelivery, WebhookEndpoint, WebhookSubscription


def test_webhook_models_are_registered_with_expected_tables() -> None:
    assert WebhookEndpoint.__tablename__ == "webhook_endpoints"
    assert WebhookSubscription.__tablename__ == "webhook_subscriptions"
    assert WebhookDelivery.__tablename__ == "webhook_deliveries"
