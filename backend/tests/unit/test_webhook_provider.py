"""Webhook Provider 单元测试。"""

import hashlib
import hmac
import json

import httpx
import pytest

from app.infrastructure.providers.webhook import WebhookProvider
from app.services.integration.contract import IntegrationEvent


@pytest.fixture
def event() -> IntegrationEvent:
    """生成不依赖数据库的统一事件测试数据。"""
    from uuid import uuid4

    return IntegrationEvent(
        tenant_id=uuid4(),
        event_type="workflow.execution.completed",
        source="workflow",
        subject="execution-1",
        idempotency_key="event-1",
        payload={"result": "ok"},
    )


def test_build_request_uses_stable_signed_event_envelope(event: IntegrationEvent) -> None:
    """验证签名针对实际发送字节计算，并包含事件身份与幂等头。"""
    provider = WebhookProvider("https://example.com/hooks", "secret")

    request = provider.build_request(event)

    expected = hmac.new(b"secret", request.body, hashlib.sha256).hexdigest()
    assert request.headers["X-Webhook-Signature"] == f"sha256={expected}"
    assert request.headers["X-Event-ID"] == str(event.event_id)
    assert request.headers["X-Event-Type"] == event.event_type
    assert request.headers["Idempotency-Key"] == event.idempotency_key
    assert json.loads(request.body) == event.as_dict()


def test_endpoint_rejects_credentials_and_fragment() -> None:
    """验证 endpoint 不允许把凭据或 fragment 混入外部请求地址。"""
    with pytest.raises(ValueError):
        WebhookProvider("https://user:pass@example.com/hooks", "secret")
    with pytest.raises(ValueError):
        WebhookProvider("https://example.com/hooks#fragment", "secret")


@pytest.mark.asyncio
async def test_send_uses_injected_client_and_raises_on_non_2xx(event: IntegrationEvent) -> None:
    """验证 Provider 使用注入客户端，并把 HTTP 失败交给上层重试策略。"""
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(503, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = WebhookProvider("https://example.com/hooks", "secret", client=client)
        with pytest.raises(httpx.HTTPStatusError):
            await provider.send(event)

    assert len(requests) == 1
    assert requests[0].headers["X-Event-ID"] == str(event.event_id)
