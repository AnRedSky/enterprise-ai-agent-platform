"""Webhook HTTP Provider。

Provider 只负责一次 HTTP 请求；Secret 在运行时解析，endpoint 在请求前执行 SSRF/出口策略。
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx

from app.services.integration.security import DEFAULT_WEBHOOK_ENDPOINT_POLICY, WebhookEndpointPolicy
from app.services.integration.secrets import EnvironmentSecretResolver, SecretResolver


class WebhookHTTPProvider:
    """执行一次带 HMAC 签名的安全 Webhook POST。"""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        secret_resolver: SecretResolver | None = None,
        endpoint_policy: WebhookEndpointPolicy | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds 必须大于 0")
        self.timeout_seconds = timeout_seconds
        self.secret_resolver = secret_resolver or EnvironmentSecretResolver()
        self.endpoint_policy = endpoint_policy or DEFAULT_WEBHOOK_ENDPOINT_POLICY
        self.client = client

    async def send(self, delivery: Any, context: dict[str, Any]) -> int:
        destination = context["destination"]
        url = self.endpoint_policy.validate(str(destination["url"]))
        headers = {str(key): str(value) for key, value in destination.get("headers", {}).items()}
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("X-Integration-Event-Id", str(delivery.integration_event_id))
        payload = context["payload"]
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        secret_ref = destination.get("secret_ref")
        if not secret_ref:
            raise RuntimeError("Webhook Destination 未配置 secret_ref")
        secret = self.secret_resolver.resolve(str(secret_ref))
        headers["X-Webhook-Signature"] = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if self.client is not None:
            response = await self.client.post(url, content=body, headers=headers, timeout=self.timeout_seconds)
        else:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = await client.post(url, content=body, headers=headers)
        if not 200 <= response.status_code < 300:
            raise WebhookDeliveryHTTPError(response.status_code, response.text[:1000])
        return response.status_code


class WebhookDeliveryHTTPError(RuntimeError):
    """外部 Webhook 返回非成功 HTTP 状态。"""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Webhook returned HTTP {status_code}: {body}")
        self.status_code = status_code
