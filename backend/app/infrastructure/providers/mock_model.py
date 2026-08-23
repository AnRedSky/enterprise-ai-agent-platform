"""模型 Mock Provider 技术适配。

模块职责：为离线测试和显式 mock 模型名提供确定性模型响应，同时保留 HTTP 错误场景测试能力。
边界：仅用于测试/本地开发；不参与生产 Provider 路由治理，不伪装为真实外部模型成功。
关键外部依赖：FastAPI HTTPException 与 model Contract。
"""

import asyncio
from typing import AsyncIterator

from fastapi import HTTPException

from .model import ModelResult


class MockModelProvider:
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
