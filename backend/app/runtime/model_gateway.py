from typing import AsyncIterator
from uuid import UUID

from app.core.config import settings
from app.runtime.openai_provider import OpenAICompatibleProvider
from app.runtime.provider import ModelResult


class MockProvider:
    async def complete(self, model: str, messages: list[dict]) -> ModelResult:
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

    async def generate(
        self,
        model: str,
        messages: list[dict],
        session_id: UUID | None = None,
    ) -> ModelResult:
        return await self.provider.complete(model, messages)

    async def stream(
        self,
        model: str,
        messages: list[dict],
        session_id: UUID | None = None,
    ) -> AsyncIterator[str]:
        async for chunk in self.provider.stream(model, messages):
            if chunk:
                yield chunk
