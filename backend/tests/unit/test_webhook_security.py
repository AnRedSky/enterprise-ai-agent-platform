from __future__ import annotations

import os

import pytest

from app.services.integration.security import WebhookEndpointPolicy, WebhookEndpointSecurityError
from app.services.integration.secrets import EnvironmentSecretResolver, MappingSecretResolver, SecretResolutionError


def test_environment_secret_resolver_requires_explicit_env_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBHOOK_TEST_SECRET", "secret-value")
    assert EnvironmentSecretResolver().resolve("env://WEBHOOK_TEST_SECRET") == "secret-value"
    with pytest.raises(SecretResolutionError):
        EnvironmentSecretResolver().resolve("secret-value")


def test_environment_secret_resolver_does_not_leak_missing_secret() -> None:
    os.environ.pop("WEBHOOK_MISSING_SECRET", None)
    with pytest.raises(SecretResolutionError, match="secret 未配置"):
        EnvironmentSecretResolver().resolve("env://WEBHOOK_MISSING_SECRET")


def test_mapping_secret_resolver_supports_dependency_injection() -> None:
    resolver = MappingSecretResolver({"test://secret": "value"})
    assert resolver.resolve("test://secret") == "value"
    with pytest.raises(SecretResolutionError):
        resolver.resolve("test://missing")


def test_webhook_policy_rejects_local_addresses() -> None:
    with pytest.raises(WebhookEndpointSecurityError):
        WebhookEndpointPolicy().validate("https://127.0.0.1/callback")
    with pytest.raises(WebhookEndpointSecurityError):
        WebhookEndpointPolicy().validate("https://localhost/callback")


def test_webhook_policy_rejects_credentials_and_non_https() -> None:
    policy = WebhookEndpointPolicy()
    with pytest.raises(WebhookEndpointSecurityError):
        policy.validate("http://example.com/callback")
    with pytest.raises(WebhookEndpointSecurityError):
        policy.validate("https://user:pass@example.com/callback")


def test_webhook_policy_allows_explicit_enterprise_egress_host() -> None:
    policy = WebhookEndpointPolicy(allowed_hosts=frozenset({"webhook.example.internal"}), allowed_ports=frozenset({443}))
    assert policy.validate("https://webhook.example.internal/callback") == "https://webhook.example.internal/callback"
