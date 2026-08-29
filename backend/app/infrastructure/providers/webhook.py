"""Webhook 外部投递 Provider。

职责：将统一 IntegrationEvent 编码为带签名的 HTTP Webhook 请求，并负责发送。
边界：不负责 Durable Event Claim、重试、租约或 Trigger 生命周期；这些规则由 Integration 领域服务与 Trigger 领域服务负责。
关键外部依赖：httpx。
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.services.integration.contract import IntegrationEvent


@dataclass(frozen=True, slots=True)
class WebhookRequest:
    """描述一次已经规范化的 Webhook HTTP 请求。"""

    url: str
    body: bytes
    headers: dict[str, str]


class WebhookProvider:
    """将 IntegrationEvent 投递到外部 Webhook endpoint。

    Args:
        endpoint: 外部 HTTPS/HTTP endpoint。
        secret: 用于 HMAC-SHA256 签名的 Secret，仅保存在运行时内存。
        timeout_seconds: 单次 HTTP 请求超时时间。
        client: 可选 HTTPX 异步客户端，便于复用连接池和测试隔离。
    """

    def __init__(
        self,
        endpoint: str,
        secret: str,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """创建 Webhook Provider，并校验 endpoint 与运行参数。"""
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Webhook endpoint 必须为有效的 HTTP/HTTPS URL")
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("Webhook endpoint 不得包含用户凭据或 URL fragment")
        if not secret:
            raise ValueError("Webhook secret 不能为空")
        if timeout_seconds <= 0:
            raise ValueError("Webhook timeout_seconds 必须大于 0")
        self.endpoint = endpoint
        self.secret = secret
        self.timeout_seconds = timeout_seconds
        self._client = client

    @staticmethod
    def _body(event: IntegrationEvent | dict[str, Any]) -> bytes:
        """生成稳定 JSON 请求体，确保签名计算与实际发送字节完全一致。"""
        payload = event.as_dict() if isinstance(event, IntegrationEvent) else event
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def build_request(self, event: IntegrationEvent | dict[str, Any]) -> WebhookRequest:
        """构造带标准事件身份、幂等键和 HMAC 签名的 Webhook 请求。

        Args:
            event: 统一 IntegrationEvent 或已经规范化的事件字典。
        Returns:
            包含 endpoint、请求体和请求头的 WebhookRequest。
        """
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
        """发送一次 Webhook 请求；非 2xx 响应作为异常交给上层可靠投递策略处理。

        Args:
            event: 要投递的统一 IntegrationEvent 或事件字典。
        Raises:
            httpx.HTTPStatusError: endpoint 返回非 2xx 响应。
            httpx.HTTPError: 网络、连接或超时错误。
        """
        request = self.build_request(event)
        if self._client is not None:
            response = await self._client.post(
                request.url,
                content=request.body,
                headers=request.headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                request.url,
                content=request.body,
                headers=request.headers,
            )
            response.raise_for_status()
