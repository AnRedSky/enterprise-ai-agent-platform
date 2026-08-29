"""Webhook HTTP Provider。

Provider 只负责一次 HTTP 请求，不参与 Delivery 状态机、重试和租约。
"""

from __future__ import annotations

from typing import Any

import httpx


class WebhookHTTPProvider:
    """使用异步 HTTP 客户端执行单次 Webhook POST。"""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds 必须大于 0")
        self.timeout_seconds = timeout_seconds

    async def send(self, delivery: Any, context: dict[str, Any]) -> int:
        """发送 JSON Webhook；非 2xx 响应转为可重试异常。"""
        destination = context["destination"]
        headers = {str(key): str(value) for key, value in destination.get("headers", {}).items()}
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("X-Integration-Event-Id", str(delivery.integration_event_id))
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
            response = await client.post(destination["url"], json=context["payload"], headers=headers)
        if not 200 <= response.status_code < 300:
            raise WebhookDeliveryHTTPError(response.status_code, response.text[:1000])
        return response.status_code


class WebhookDeliveryHTTPError(RuntimeError):
    """外部 Webhook 返回非成功 HTTP 状态。"""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Webhook returned HTTP {status_code}: {body}")
        self.status_code = status_code
