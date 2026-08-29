"""Outbound Webhook endpoint security policy.

Default policy is deny-by-network: only HTTP(S) URLs are accepted and hostnames resolving
into loopback, private, link-local, multicast, unspecified or reserved networks are rejected.
An explicit hostname allowlist may be supplied for controlled enterprise egress.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse


class WebhookEndpointSecurityError(ValueError):
    """Raised when a webhook endpoint violates the outbound security policy."""


@dataclass(frozen=True, slots=True)
class WebhookEndpointPolicy:
    """SSRF/egress policy applied immediately before an outbound request."""

    allowed_hosts: frozenset[str] = frozenset()
    allow_http: bool = False
    allowed_ports: frozenset[int] = frozenset({443})

    def validate(self, endpoint: str) -> str:
        parsed = urlparse(endpoint)
        scheme = parsed.scheme.lower()
        if scheme not in ({"https"} if not self.allow_http else {"http", "https"}):
            raise WebhookEndpointSecurityError("Webhook endpoint 只允许 HTTPS（HTTP 必须显式开启）")
        if parsed.username or parsed.password or parsed.fragment or not parsed.hostname:
            raise WebhookEndpointSecurityError("Webhook endpoint 不得包含凭据、fragment，且必须包含 hostname")
        try:
            port = parsed.port
        except ValueError as exc:
            raise WebhookEndpointSecurityError("Webhook endpoint 端口无效") from exc
        if port is not None and port not in self.allowed_ports:
            raise WebhookEndpointSecurityError("Webhook endpoint 端口不在允许范围")

        hostname = parsed.hostname.rstrip(".").lower()
        if hostname in self.allowed_hosts:
            return parsed.geturl()

        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(hostname, port or (443 if scheme == "https" else 80), type=socket.SOCK_STREAM)
            }
        except OSError as exc:
            raise WebhookEndpointSecurityError("Webhook endpoint DNS 解析失败") from exc
        if not addresses:
            raise WebhookEndpointSecurityError("Webhook endpoint 未解析到地址")
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
                raise WebhookEndpointSecurityError("Webhook endpoint 解析到禁止访问的内部/保留网络地址")
        return parsed.geturl()


DEFAULT_WEBHOOK_ENDPOINT_POLICY = WebhookEndpointPolicy()
