from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from app.services.integration.secrets import MappingSecretResolver
from app.services.integration.security import WebhookEndpointPolicy
from app.services.integration.webhook_delivery import WebhookDeliveryWorker
from app.services.integration.webhook_provider import WebhookDeliveryHTTPError, WebhookHTTPProvider


def test_retry_at_is_capped() -> None:
    now = datetime(2026, 8, 29, tzinfo=UTC).replace(tzinfo=None)
    assert WebhookDeliveryWorker.retry_at(now, 1) == datetime(2026, 8, 29, 0, 0, 2)
    assert WebhookDeliveryWorker.retry_at(now, 10) == datetime(2026, 8, 29, 0, 5, 0)


def test_retry_at_rejects_invalid_arguments() -> None:
    now = datetime(2026, 8, 29)
    with pytest.raises(ValueError):
        WebhookDeliveryWorker.retry_at(now, 0)


def _test_provider(client: httpx.AsyncClient) -> WebhookHTTPProvider:
    """构造隔离的 Webhook Provider 测试实例，显式注入 endpoint 与 Secret 依赖。"""
    return WebhookHTTPProvider(
        client=client,
        endpoint_policy=WebhookEndpointPolicy(allowed_hosts=frozenset({"example.test"})),
        secret_resolver=MappingSecretResolver({"test-secret": "unit-test-secret"}),
    )


@pytest.mark.asyncio
async def test_provider_returns_success_status() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["X-Integration-Event-Id"] == "event-1"
        assert request.headers["Content-Type"] == "application/json"
        assert request.headers["X-Webhook-Signature"].startswith("sha256=")
        return httpx.Response(202)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        provider = _test_provider(client)
        delivery = SimpleNamespace(integration_event_id="event-1")
        status = await provider.send(
            delivery,
            {
                "payload": {"event": "created"},
                "destination": {"url": "https://example.test/hook", "headers": {}, "secret_ref": "test-secret"},
            },
        )
        assert status == 202
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_provider_converts_non_2xx_to_retryable_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="temporarily unavailable")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        provider = _test_provider(client)
        with pytest.raises(WebhookDeliveryHTTPError) as exc_info:
            await provider.send(
                SimpleNamespace(integration_event_id="event-2"),
                {
                    "payload": {},
                    "destination": {"url": "https://example.test/hook", "headers": {}, "secret_ref": "test-secret"},
                },
            )
        assert exc_info.value.status_code == 503
    finally:
        await client.aclose()
