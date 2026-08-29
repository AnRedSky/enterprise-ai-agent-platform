from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.services.runtime_operations.provider_health import RuntimeProviderHealthService


class _DB:
    def __init__(self, provider): self.provider = provider; self.added = []
    async def scalar(self, _statement): return self.provider
    def add(self, item): self.added.append(item)


class _Response:
    status_code = 204


class _Client:
    def __init__(self, **_kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *_args): return False
    async def get(self, _url): return _Response()


@pytest.mark.asyncio
async def test_provider_health_probe_is_tenant_scoped_and_records_audit(monkeypatch):
    tenant_id = uuid4()
    provider = SimpleNamespace(id=uuid4(), tenant_id=tenant_id, name="openai", provider_type="model", config={"healthcheck_url": "https://example.com/health", "capabilities": ["chat"]}, health_status="unknown")
    db = _DB(provider)
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    result = await RuntimeProviderHealthService().probe(db, tenant_id, provider.id, "actor-1")
    assert result.status == "healthy"
    assert result.http_status == 204
    assert provider.health_status == "healthy"
    assert db.added[0].action == "provider.health_probe"
    assert db.added[0].tenant_id == tenant_id


@pytest.mark.asyncio
async def test_provider_health_probe_rejects_missing_endpoint():
    tenant_id = uuid4()
    provider = SimpleNamespace(id=uuid4(), tenant_id=tenant_id, config={}, health_status="unknown")
    with pytest.raises(ValueError, match="healthcheck_url"):
        await RuntimeProviderHealthService().probe(_DB(provider), tenant_id, provider.id, "actor-1")
