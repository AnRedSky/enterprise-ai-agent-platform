import asyncio
from typing import AsyncIterator
from uuid import UUID

from fastapi import HTTPException

from app.core.config import settings
from app.runtime.openai_provider import OpenAICompatibleProvider
from app.runtime.provider import ModelResult


class MockProvider:
    async def complete(self, model: str, messages: list[dict]) -> ModelResult:
        if model == "mock-http-404":
            raise HTTPException(404, "Mock provider HTTP 404")
        if model == "mock-http-503":
            raise HTTPException(503, "Mock provider HTTP 503")
        if model == "mock-slow-success":
            await asyncio.sleep(0.25)
        return ModelResult(content=f"【Mock】模型={model}\n{messages[-1]['content']}", model=model)

    async def stream(self, model: str, messages: list[dict]) -> AsyncIterator[str]:
        result = await self.complete(model, messages)
        for token in result.content.split():
            yield token + " "


class ModelGateway:
    """Unified model entrypoint; provider details must not leak into Agent Runtime."""

    def __init__(self, provider=None):
        self.provider = provider or (
            OpenAICompatibleProvider()
            if settings.model_provider == "openai-compatible"
            else MockProvider()
        )

    def _provider_for_model(self, model: str):
        """Route explicit mock models to the deterministic local provider."""
        if isinstance(self.provider, OpenAICompatibleProvider) and model.startswith("mock-"):
            return MockProvider()
        return self.provider

    async def generate(
        self,
        model: str,
        messages: list[dict],
        session_id: UUID | None = None,
    ) -> ModelResult:
        provider = self._provider_for_model(model)
        try:
            return await provider.complete(model, messages)
        except Exception:
            if not settings.model_fallback_to_mock or isinstance(provider, MockProvider):
                raise
            # Local development resilience only: never hide provider failures
            # in a real-provider quality gate unless this flag is explicitly on.
            return await MockProvider().complete(settings.model_default_name, messages)

    async def stream(
        self,
        model: str,
        messages: list[dict],
        session_id: UUID | None = None,
    ) -> AsyncIterator[str]:
        provider = self._provider_for_model(model)
        try:
            async for chunk in provider.stream(model, messages):
                if chunk:
                    yield chunk
        except Exception:
            if not settings.model_fallback_to_mock or isinstance(provider, MockProvider):
                raise
            async for chunk in MockProvider().stream(settings.model_default_name, messages):
                if chunk:
                    yield chunk
