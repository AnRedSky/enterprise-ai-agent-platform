import json
from typing import AsyncIterator

import httpx

from app.core.config import settings
from app.runtime.model_gateway import ModelResult, ModelUsage


class OpenAICompatibleProvider:
    """OpenAI-compatible chat-completions provider with bounded timeout."""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.model_api_key}",
            "Content-Type": "application/json",
        }

    def _url(self) -> str:
        if not settings.model_base_url or not settings.model_api_key:
            raise RuntimeError("MODEL_BASE_URL and MODEL_API_KEY are required")
        return f"{settings.model_base_url.rstrip('/')}/chat/completions"

    async def complete(self, model: str, messages: list[dict]) -> ModelResult:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self._url(),
                headers=self._headers(),
                json={"model": model, "messages": messages, "stream": False},
            )
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

    async def stream(self, model: str, messages: list[dict]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                self._url(),
                headers=self._headers(),
                json={"model": model, "messages": messages, "stream": True},
            ) as response:
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
