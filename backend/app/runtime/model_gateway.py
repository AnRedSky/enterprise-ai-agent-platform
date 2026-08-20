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
        """Route explicit mock models to the deterministic local provider.

        This keeps the local smoke-test contract stable even when a developer's
        .env enables an OpenAI-compatible provider for other agents.
        An explicitly injected provider is still always honored by tests/callers.
        """
        if isinstance(self.provider, OpenAICompatibleProvider) and model.startswith("mock-"):
            return MockProvider()
        return self.provider

    async def generate(
        self,
        model: str,
        messages: list[dict],
        session_id: UUID | None = None,
    ) -> ModelResult:
        return await self._provider_for_model(model).complete(model, messages)

    async def stream(
        self,
        model: str,
        messages: list[dict],
        session_id: UUID | None = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._provider_for_model(model).stream(model, messages):
            if chunk:
                yield chunk
