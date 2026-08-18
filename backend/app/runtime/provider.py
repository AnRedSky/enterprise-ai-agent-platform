from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass
class ModelUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass
class ModelResult:
    content: str
    usage: ModelUsage | None = None
    model: str | None = None


class ModelProvider(Protocol):
    async def complete(self, model: str, messages: list[dict]) -> ModelResult: ...
    async def stream(self, model: str, messages: list[dict]) -> AsyncIterator[str]: ...
