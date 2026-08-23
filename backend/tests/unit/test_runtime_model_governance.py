from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

from app.services.model_provider_governance_contract import FallbackReason
from app.services.runtime_model_governance import RuntimeModelGovernanceService, RuntimeProviderCandidate


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (httpx.ConnectError("connect"), FallbackReason.CONNECTIVITY),
        (httpx.ConnectTimeout("connect timeout"), FallbackReason.CONNECTIVITY),
        (httpx.ReadTimeout("read timeout"), FallbackReason.TIMEOUT),
        (httpx.WriteTimeout("write timeout"), FallbackReason.TIMEOUT),
        (httpx.PoolTimeout("pool timeout"), FallbackReason.TIMEOUT),
        (HTTPException(429, "rate"), FallbackReason.RATE_LIMIT),
        (HTTPException(503, "provider"), FallbackReason.PROVIDER_5XX),
        (HTTPException(400, "bad request"), None),
    ],
)
def test_fallback_reason_is_bounded_to_governance_contract(error, expected):
    assert RuntimeModelGovernanceService.fallback_reason(error) == expected


@pytest.mark.asyncio
async def test_invoke_tries_next_governed_candidate_without_mock_fallback(monkeypatch):
    calls = []

    class Gateway:
        async def generate(self, model, messages, **kwargs):
            calls.append((model, kwargs["model_profile"].id, kwargs["model_provider"].id))
            if len(calls) == 1:
                raise HTTPException(503, "provider unavailable")
            return SimpleNamespace(content="real provider success")

    service = RuntimeModelGovernanceService(None, gateway=Gateway())
    provider_one = SimpleNamespace(id=uuid4())
    provider_two = SimpleNamespace(id=uuid4())
    profile_one = SimpleNamespace(id=uuid4(), model_name="provider-model-1")
    profile_two = SimpleNamespace(id=uuid4(), model_name="provider-model-2")

    async def resolve(_request, _user_id):
        return [
            RuntimeProviderCandidate(profile_one, provider_one),
            RuntimeProviderCandidate(profile_two, provider_two),
        ]

    monkeypatch.setattr(service, "resolve", resolve)
    result = await service.invoke(SimpleNamespace(), uuid4(), [{"role": "user", "content": "hello"}])

    assert result.content == "real provider success"
    assert [item[0] for item in calls] == ["provider-model-1", "provider-model-2"]


@pytest.mark.asyncio
async def test_invoke_reports_attempt_identity_without_exposing_provider_secrets(monkeypatch):
    class Gateway:
        async def generate(self, model, messages, **kwargs):
            raise httpx.ConnectError("connect")

    service = RuntimeModelGovernanceService(None, gateway=Gateway())
    provider = SimpleNamespace(id=uuid4())
    profile = SimpleNamespace(id=uuid4(), model_name="governed-model", model_type="chat")
    candidate = RuntimeProviderCandidate(profile, provider)
    attempts = []

    async def resolve(_request, _user_id):
        return [candidate]

    async def on_attempt(item, request_id, outcome, reason, result):
        attempts.append((item, request_id, outcome, reason, result))

    monkeypatch.setattr(service, "resolve", resolve)
    with pytest.raises(httpx.ConnectError):
        await service.invoke(
            SimpleNamespace(),
            uuid4(),
            [{"role": "user", "content": "hello"}],
            on_attempt=on_attempt,
        )

    assert len(attempts) == 1
    item, request_id, outcome, reason, result = attempts[0]
    assert item.profile.id == profile.id
    assert item.provider.id == provider.id
    assert request_id
    assert outcome == "failed"
    assert reason == FallbackReason.CONNECTIVITY
    assert result is None


@pytest.mark.asyncio
async def test_invoke_does_not_fallback_on_non_governed_error(monkeypatch):
    calls = 0

    class Gateway:
        async def generate(self, model, messages, **kwargs):
            nonlocal calls
            calls += 1
            raise HTTPException(400, "invalid request")

    service = RuntimeModelGovernanceService(None, gateway=Gateway())
    candidate = RuntimeProviderCandidate(SimpleNamespace(id=uuid4(), model_name="model"), SimpleNamespace(id=uuid4()))

    async def resolve(_request, _user_id):
        return [candidate]

    monkeypatch.setattr(service, "resolve", resolve)
    with pytest.raises(HTTPException) as exc_info:
        await service.invoke(SimpleNamespace(), uuid4(), [{"role": "user", "content": "hello"}])

    assert exc_info.value.status_code == 400
    assert calls == 1
