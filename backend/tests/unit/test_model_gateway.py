from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from app.infrastructure.providers.mock_model import MockModelProvider
from app.infrastructure.providers.openai_model import OpenAICompatibleProvider
from app.runtime.model import ModelGateway


@pytest.mark.asyncio
async def test_mock_provider():
    gateway = ModelGateway(MockModelProvider())
    result = await gateway.generate("mock-model", [{"role": "user", "content": "hello"}])
    assert "hello" in result.content


@pytest.mark.asyncio
async def test_mock_http_503_provider_is_deterministic():
    gateway = ModelGateway(MockModelProvider())
    with pytest.raises(HTTPException) as exc:
        await gateway.generate("mock-http-503", [{"role": "user", "content": "circuit"}])
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_openai_provider_http_status_preserves_503_for_governed_profile():
    provider = AsyncMock()
    request = httpx.Request("POST", "http://127.0.0.1:8870/v1/chat/completions")
    response = httpx.Response(503, request=request)
    provider.complete.side_effect = httpx.HTTPStatusError(
        "Server error '503 Service Unavailable'",
        request=request,
        response=response,
    )
    gateway = ModelGateway(provider)
    profile = SimpleNamespace(model_name="resume-fixture-model", parameters={})

    with pytest.raises(HTTPException) as exc:
        await gateway.generate("legacy-model", [{"role": "user", "content": "resume"}], model_profile=profile)

    assert exc.value.status_code == 503
    assert "503 Service Unavailable" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_openai_provider_http_status_still_uses_local_fallback_without_profile(monkeypatch):
    provider = AsyncMock()
    request = httpx.Request("POST", "http://127.0.0.1:8870/v1/chat/completions")
    response = httpx.Response(503, request=request)
    provider.complete.side_effect = httpx.HTTPStatusError(
        "Server error '503 Service Unavailable'",
        request=request,
        response=response,
    )
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_fallback_to_mock", True)
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_default_name", "fallback-model")
    gateway = ModelGateway(provider)

    result = await gateway.generate("primary-model", [{"role": "user", "content": "fallback"}])

    assert result.model == "fallback-model"
    assert "fallback" in result.content


@pytest.mark.asyncio
async def test_openai_provider_stream_http_status_preserves_503_for_governed_profile():
    request = httpx.Request("POST", "http://127.0.0.1:8870/v1/chat/completions")
    response = httpx.Response(503, request=request)

    class FailingStreamProvider:
        async def stream(self, model, messages, parameters=None):
            raise httpx.HTTPStatusError(
                "Server error '503 Service Unavailable'",
                request=request,
                response=response,
            )
            yield "unreachable"

    gateway = ModelGateway(FailingStreamProvider())
    profile = SimpleNamespace(model_name="resume-fixture-model", parameters={})

    with pytest.raises(HTTPException) as exc:
        async for _ in gateway.stream("legacy-model", [{"role": "user", "content": "resume"}], model_profile=profile):
            pass

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_mock_model_routes_to_mock_provider(monkeypatch):
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_provider", "openai-compatible")
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_base_url", "http://127.0.0.1:9")
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_api_key", "test-key")

    gateway = ModelGateway()
    assert isinstance(gateway.provider, OpenAICompatibleProvider)

    result = await gateway.generate("mock-model", [{"role": "user", "content": "scenario-ok"}])

    assert result.model == "mock-model"
    assert "scenario-ok" in result.content


@pytest.mark.asyncio
async def test_openai_compatible_provider_falls_back_to_mock_for_local_development(monkeypatch):
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_provider", "openai-compatible")
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_base_url", "http://127.0.0.1:9")
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_api_key", "ollama")
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_fallback_to_mock", True)
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_default_name", "qwen3:0.6b")

    result = await ModelGateway().generate(
        "qwen3:0.6b", [{"role": "user", "content": "offline-ok"}]
    )

    assert "offline-ok" in result.content
    assert result.model == "qwen3:0.6b"


@pytest.mark.asyncio
async def test_openai_compatible_provider_does_not_fallback_when_disabled(monkeypatch):
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_provider", "openai-compatible")
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_base_url", "http://127.0.0.1:9")
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_api_key", "ollama")
    monkeypatch.setattr("app.runtime.model.gateway.settings.model_fallback_to_mock", False)

    with pytest.raises(Exception):
        await ModelGateway().generate(
            "qwen3:0.6b", [{"role": "user", "content": "must-fail"}]
        )
