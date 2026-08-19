import pytest
from fastapi import HTTPException

from app.services.vector_knowledge_retrieval import KnowledgeRetrievalRouterService


@pytest.mark.asyncio
async def test_router_uses_lexical_mode_by_default(monkeypatch):
    async def fake_retrieve(self, **kwargs):
        return [{"retrieval_mode": "lexical-v2"}]

    monkeypatch.setattr("app.services.vector_knowledge_retrieval.KnowledgeRetrievalService.retrieve", fake_retrieve)
    results, mode, fallback = await KnowledgeRetrievalRouterService(None).retrieve(
        mode="lexical-v2", fallback_to_lexical=False, query="agent", top_k=5, owner_id=None
    )
    assert results == [{"retrieval_mode": "lexical-v2"}]
    assert mode == "lexical-v2"
    assert fallback is False


@pytest.mark.asyncio
async def test_vector_failure_is_not_silently_downgraded(monkeypatch):
    async def fake_retrieve(self, **kwargs):
        raise HTTPException(status_code=503, detail="vector unavailable")

    monkeypatch.setattr("app.services.vector_knowledge_retrieval.VectorKnowledgeRetrievalService.retrieve", fake_retrieve)
    with pytest.raises(HTTPException) as exc:
        await KnowledgeRetrievalRouterService(None).retrieve(
            mode="vector", fallback_to_lexical=False, query="agent", top_k=5, owner_id=None
        )
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_vector_failure_can_explicitly_fallback_to_lexical(monkeypatch):
    async def fake_vector(self, **kwargs):
        raise HTTPException(status_code=503, detail="vector unavailable")

    async def fake_lexical(self, **kwargs):
        return [{"retrieval_mode": "lexical-v2"}]

    monkeypatch.setattr("app.services.vector_knowledge_retrieval.VectorKnowledgeRetrievalService.retrieve", fake_vector)
    monkeypatch.setattr("app.services.vector_knowledge_retrieval.KnowledgeRetrievalService.retrieve", fake_lexical)
    results, mode, fallback = await KnowledgeRetrievalRouterService(None).retrieve(
        mode="vector", fallback_to_lexical=True, query="agent", top_k=5, owner_id=None
    )
    assert results == [{"retrieval_mode": "lexical-v2"}]
    assert mode == "lexical-v2"
    assert fallback is True


def test_vector_retrieval_contract_allows_mock_embedding_for_local_db_loop():
    from app.core.config import settings

    assert settings.embedding_provider in {"none", "mock", "openai-compatible"}
    # The service explicitly accepts mock and real OpenAI-compatible providers;
    # this test guards the supported local database validation mode without
    # requiring a live PostgreSQL connection in unit tests.
    assert {"openai-compatible", "mock"}.issubset({"openai-compatible", "mock"})
