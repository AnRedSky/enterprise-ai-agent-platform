"""Webhook 外部投递 Provider。"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.services.integration.contract import IntegrationEvent
from app.services.integration.security import DEFAULT_WEBHOOK_ENDPOINT_POLICY, WebhookEndpointPolicy


@dataclass(frozen=True, slots=True)
class WebhookRequest:
    """描述一次已经规范化的 Webhook HTTP 请求。"""

    url: str
    body: bytes
    headers: dict[str, str]


class WebhookProvider:
    """将 IntegrationEvent 投递到外部 Webhook endpoint，并执行 SSRF/出口策略。"""

    def __init__(
        self,
        endpoint: str,
        secret: str,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
        endpoint_policy: WebhookEndpointPolicy | None = None,
    ) -> None:
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Webhook endpoint 必须为有效的 HTTP/HTTPS URL")
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("Webhook endpoint 不得包含用户凭据或 URL fragment")
        if not secret:
            raise ValueError("Webhook secret 不能为空")
        if timeout_seconds <= 0:
            raise ValueError("Webhook timeout_seconds 必须大于 0")
        self.endpoint_policy = endpoint_policy or DEFAULT_WEBHOOK_ENDPOINT_POLICY
        self.endpoint_policy.validate(endpoint)
        self.endpoint = endpoint
        self.secret = secret
        self.timeout_seconds = timeout_seconds
        self._client = client

    @staticmethod
    def _body(event: IntegrationEvent | dict[str, Any]) -> bytes:
        payload = event.as_dict() if isinstance(event, IntegrationEvent) else event
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def build_request(self, event: IntegrationEvent | dict[str, Any]) -> WebhookRequest:
        body = self._body(event)
        signature = hmac.new(self.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        payload = event.as_dict() if isinstance(event, IntegrationEvent) else event
        return WebhookRequest(
            url=self.endpoint,
            body=body,
            headers={
                "Content-Type": "application/json",
                "X-Event-ID": str(payload.get("event_id", "")),
                "X-Event-Type": str(payload.get("event_type", "")),
                "X-Event-Schema-Version": str(payload.get("schema_version", "1")),
                "Idempotency-Key": str(payload.get("idempotency_key", "")),
                "X-Webhook-Signature": f"sha256={signature}",
            },
        )

    async def send(self, event: IntegrationEvent | dict[str, Any]) -> None:
        request = self.build_request(event)
        if self._client is not None:
            response = await self._client.post(request.url, content=request.body, headers=request.headers, timeout=self.timeout_seconds)
            response.raise_for_status()
            return
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(request.url, content=request.body, headers=request.headers)
            response.raise_for_status()
