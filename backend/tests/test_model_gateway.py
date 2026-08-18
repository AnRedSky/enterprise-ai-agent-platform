import pytest

from app.runtime.model_gateway import ModelGateway, MockProvider
from app.runtime.openai_provider import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_mock_provider():
    gateway = ModelGateway(MockProvider())
    result = await gateway.generate("mock-model", [{"role": "user", "content": "hello"}])
    assert "hello" in result.content


@pytest.mark.asyncio
async def test_mock_model_routes_to_mock_provider(monkeypatch):
    monkeypatch.setattr("app.runtime.model_gateway.settings.model_provider", "openai-compatible")
    monkeypatch.setattr("app.runtime.model_gateway.settings.model_base_url", "http://127.0.0.1:9")
    monkeypatch.setattr("app.runtime.model_gateway.settings.model_api_key", "test-key")

    gateway = ModelGateway()
    assert isinstance(gateway.provider, OpenAICompatibleProvider)

    result = await gateway.generate("mock-model", [{"role": "user", "content": "scenario-ok"}])

    assert result.model == "mock-model"
    assert "scenario-ok" in result.content
