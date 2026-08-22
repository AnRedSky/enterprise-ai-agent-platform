import asyncio
import os
from typing import AsyncIterator
from uuid import UUID

from fastapi import HTTPException

from app.core.config import settings
from app.runtime.openai_provider import OpenAICompatibleProvider
from app.runtime.provider import ModelResult


class MockProvider:
    async def complete(self, model: str, messages: list[dict], parameters: dict | None = None) -> ModelResult:
        if model == "mock-http-404":
            raise HTTPException(404, "Mock provider HTTP 404")
        if model == "mock-http-503":
            raise HTTPException(503, "Mock provider HTTP 503")
        if model == "mock-slow-success":
            await asyncio.sleep(0.25)
        return ModelResult(content=f"【Mock】模型={model}\n{messages[-1]['content']}", model=model)

    async def stream(self, model: str, messages: list[dict], parameters: dict | None = None) -> AsyncIterator[str]:
        result = await self.complete(model, messages, parameters)
        for token in result.content.split():
            yield token + " "


class ModelGateway:
    """Unified model entrypoint; provider details must not leak into Agent Runtime."""

    def __init__(self, provider=None):
        self.provider = provider or (OpenAICompatibleProvider() if settings.model_provider == "openai-compatible" else MockProvider())

    @staticmethod
    def _credential(provider) -> str | None:
        if provider is None or not provider.credential_ref:
            return settings.model_api_key
        return os.getenv(provider.credential_ref)

    def _provider_for_profile(self, profile=None, model_provider=None):
        if profile is None or model_provider is None:
            return self.provider
        if model_provider.provider_type in {"openai-compatible", "ollama"}:
            parameters = profile.parameters or {}
            return OpenAICompatibleProvider(
                base_url=model_provider.endpoint or settings.model_base_url,
                api_key=self._credential(model_provider),
                timeout_seconds=float(parameters.get("timeout_seconds", settings.model_timeout_seconds)),
            )
        if model_provider.provider_type == "mock":
            return MockProvider()
        raise HTTPException(422, f"不支持的 Model Provider 类型: {model_provider.provider_type}")

    @staticmethod
    def _request_parameters(profile) -> dict | None:
        if profile is None:
            return None
        return {key: value for key, value in (profile.parameters or {}).items() if key != "timeout_seconds"}

    async def generate(self, model: str, messages: list[dict], session_id: UUID | None = None, model_profile=None, model_provider=None) -> ModelResult:
        provider = self._provider_for_profile(model_profile, model_provider)
        actual_model = model_profile.model_name if model_profile is not None else model
        parameters = self._request_parameters(model_profile)
        if isinstance(provider, OpenAICompatibleProvider) and actual_model.startswith("mock-"):
            provider = MockProvider()
        try:
            return await provider.complete(actual_model, messages, parameters)
        except Exception:
            if model_profile is not None or not settings.model_fallback_to_mock or isinstance(provider, MockProvider):
                raise
            return await MockProvider().complete(settings.model_default_name, messages)

    async def stream(self, model: str, messages: list[dict], session_id: UUID | None = None, model_profile=None, model_provider=None) -> AsyncIterator[str]:
        provider = self._provider_for_profile(model_profile, model_provider)
        actual_model = model_profile.model_name if model_profile is not None else model
        parameters = self._request_parameters(model_profile)
        if isinstance(provider, OpenAICompatibleProvider) and actual_model.startswith("mock-"):
            provider = MockProvider()
        try:
            async for chunk in provider.stream(actual_model, messages, parameters):
                if chunk:
                    yield chunk
        except Exception:
            if model_profile is not None or not settings.model_fallback_to_mock or isinstance(provider, MockProvider):
                raise
            async for chunk in MockProvider().stream(settings.model_default_name, messages):
                if chunk:
                    yield chunk
