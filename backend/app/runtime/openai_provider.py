import json
from typing import AsyncIterator

import httpx

from app.core.config import settings
from app.runtime.provider import ModelResult, ModelUsage


class OpenAICompatibleProvider:
    """OpenAI-compatible chat-completions provider with bounded timeout."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout_seconds: float | None = None):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds or settings.model_timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _url(self) -> str:
        base_url = self.base_url or settings.model_base_url
        if not base_url:
            raise RuntimeError("Model Provider endpoint is required")
        return f"{base_url.rstrip('/')}/chat/completions"

    async def complete(self, model: str, messages: list[dict], parameters: dict | None = None) -> ModelResult:
        payload = {"model": model, "messages": messages, "stream": False}
        if parameters:
            payload.update(parameters)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self._url(), headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage") or {}
            return ModelResult(
                content=data["choices"][0]["message"]["content"],
                model=data.get("model", model),
                usage=ModelUsage(
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                ),
            )

    async def stream(self, model: str, messages: list[dict], parameters: dict | None = None) -> AsyncIterator[str]:
        payload = {"model": model, "messages": messages, "stream": True}
        if parameters:
            payload.update(parameters)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream("POST", self._url(), headers=self._headers(), json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    try:
                        data = json.loads(payload)
                        yield data["choices"][0].get("delta", {}).get("content", "")
                    except (ValueError, KeyError, IndexError, TypeError):
                        continue
