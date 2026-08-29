"""Runtime secret resolution for outbound Webhooks.

Secrets are never stored as plaintext in WebhookDestination. The reference is resolved at
send time by an injected resolver, allowing environment variables now and a vault/KMS adapter
later without changing the delivery worker contract.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class SecretResolutionError(RuntimeError):
    """Raised when a configured secret reference cannot be resolved."""


class SecretResolver(ABC):
    """Runtime-only secret lookup interface."""

    @abstractmethod
    def resolve(self, secret_ref: str) -> str:
        raise NotImplementedError


class EnvironmentSecretResolver(SecretResolver):
    """Resolve only explicit ``env://NAME`` references from the process environment."""

    prefix = "env://"

    def resolve(self, secret_ref: str) -> str:
        if not secret_ref or not secret_ref.startswith(self.prefix):
            raise SecretResolutionError("Webhook secret_ref 必须使用 env://NAME 形式")
        name = secret_ref[len(self.prefix):]
        if not name or not name.replace("_", "").isalnum() or name[0].isdigit():
            raise SecretResolutionError("Webhook secret_ref 的环境变量名称无效")
        value = os.getenv(name)
        if not value:
            raise SecretResolutionError(f"Webhook secret 未配置: {name}")
        return value


class MappingSecretResolver(SecretResolver):
    """测试/本地注入 resolver；生产环境应替换为 Vault/KMS 实现。"""

    def __init__(self, values: dict[str, str]) -> None:
        self._values = dict(values)

    def resolve(self, secret_ref: str) -> str:
        try:
            value = self._values[secret_ref]
        except KeyError as exc:
            raise SecretResolutionError("Webhook secret_ref 不存在") from exc
        if not value:
            raise SecretResolutionError("Webhook secret 为空")
        return value
