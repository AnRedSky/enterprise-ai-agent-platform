import pytest
from app.runtime.model_gateway import ModelGateway, MockProvider

@pytest.mark.asyncio
async def test_mock_provider():
    gateway = ModelGateway(MockProvider())
    result = await gateway.generate("mock-model", [{"role":"user","content":"hello"}])
    assert "hello" in result
