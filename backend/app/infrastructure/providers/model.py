"""模型 Provider 技术 Contract。

模块职责：定义模型调用结果、用量和 complete/stream Provider 协议，作为 Runtime 与外部模型适配之间的稳定技术边界。
边界：不实现具体模型供应商，也不包含领域路由、权限或治理规则。
关键外部依赖：Python dataclasses、typing 标准库。
"""

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

    def __contains__(self, item: str) -> bool:
        return item in self.content


class ModelProvider(Protocol):
    async def complete(self, model: str, messages: list[dict], parameters: dict | None = None) -> ModelResult: ...
    async def stream(self, model: str, messages: list[dict], parameters: dict | None = None) -> AsyncIterator[str]: ...
