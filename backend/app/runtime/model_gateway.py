from abc import ABC, abstractmethod
from dataclasses import dataclass
import httpx

@dataclass
class ModelRequest:
    model: str
    messages: list[dict]

class ModelProvider(ABC):
    @abstractmethod
    async def generate(self, request: ModelRequest): ...

class MockProvider(ModelProvider):
    async def generate(self, request):
        return f"【Mock】{request.messages[-1]['content']}"

class OpenAICompatibleProvider(ModelProvider):
    def __init__(self, base_url: str, api_key: str): self.base_url, self.api_key = base_url.rstrip('/'), api_key
    async def generate(self, request):
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{self.base_url}/chat/completions", headers={"Authorization":f"Bearer {self.api_key}"}, json={"model":request.model,"messages":request.messages})
            r.raise_for_status(); return r.json()["choices"][0]["message"]["content"]

class ModelGateway:
    def __init__(self, provider: ModelProvider): self.provider = provider
    async def generate(self, model, messages): return await self.provider.generate(ModelRequest(model, messages))
