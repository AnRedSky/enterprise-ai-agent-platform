from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

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


@pytest.mark.asyncio
async def test_provider_returns_success_status() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["X-Integration-Event-Id"] == "event-1"
        assert request.headers["Content-Type"] == "application/json"
        return httpx.Response(202)

    provider = WebhookHTTPProvider()
    transport = httpx.MockTransport(handler)
    provider_client = httpx.AsyncClient(transport=transport)

    original = httpx.AsyncClient
    httpx.AsyncClient = lambda **kwargs: provider_client  # type: ignore[method-assign]
    try:
        delivery = SimpleNamespace(integration_event_id="event-1")
        status = await provider.send(
            delivery,
            {"payload": {"event": "created"}, "destination": {"url": "https://example.test/hook", "headers": {}}},
        )
        assert status == 202
    finally:
        httpx.AsyncClient = original  # type: ignore[method-assign]
        await provider_client.aclose()


@pytest.mark.asyncio
async def test_provider_converts_non_2xx_to_retryable_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="temporarily unavailable")

    provider = WebhookHTTPProvider()
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    original = httpx.AsyncClient
    httpx.AsyncClient = lambda **kwargs: client  # type: ignore[method-assign]
    try:
        with pytest.raises(WebhookDeliveryHTTPError) as exc_info:
            await provider.send(
                SimpleNamespace(integration_event_id="event-2"),
                {"payload": {}, "destination": {"url": "https://example.test/hook", "headers": {}}},
            )
        assert exc_info.value.status_code == 503
    finally:
        httpx.AsyncClient = original  # type: ignore[method-assign]
        await client.aclose()
