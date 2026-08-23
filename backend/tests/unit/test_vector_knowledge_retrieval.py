import pytest
from fastapi import HTTPException

from app.services.retrieval_evaluation import RetrievalEvaluationObservation, aggregate_observations
from app.services.knowledge.vector_retrieval import KnowledgeRetrievalRouterService, VectorKnowledgeRetrievalService


@pytest.mark.asyncio
async def test_router_uses_lexical_mode_by_default(monkeypatch):
    async def fake_retrieve(self, **kwargs):
        return [{"retrieval_mode": "lexical-v2"}]
    monkeypatch.setattr("app.services.knowledge.vector_retrieval.KnowledgeRetrievalService.retrieve", fake_retrieve)
    results, mode, fallback = await KnowledgeRetrievalRouterService(None).retrieve(mode="lexical-v2", fallback_to_lexical=False, query="agent", top_k=5, owner_id=None)
    assert results == [{"retrieval_mode": "lexical-v2"}]
    assert mode == "lexical-v2"
    assert fallback is False


@pytest.mark.asyncio
async def test_vector_failure_is_not_silently_downgraded(monkeypatch):
    async def fake_retrieve(self, **kwargs):
        raise HTTPException(status_code=503, detail="vector unavailable")
    monkeypatch.setattr("app.services.knowledge.vector_retrieval.VectorKnowledgeRetrievalService.retrieve", fake_retrieve)
    with pytest.raises(HTTPException) as exc:
        await KnowledgeRetrievalRouterService(None).retrieve(mode="vector", fallback_to_lexical=False, query="agent", top_k=5, owner_id=None)
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_vector_failure_can_explicitly_fallback_to_lexical(monkeypatch):
    async def fake_vector(self, **kwargs):
        raise HTTPException(status_code=503, detail="vector unavailable")
    async def fake_lexical(self, **kwargs):
        return [{"retrieval_mode": "lexical-v2"}]
    monkeypatch.setattr("app.services.knowledge.vector_retrieval.VectorKnowledgeRetrievalService.retrieve", fake_vector)
    monkeypatch.setattr("app.services.knowledge.vector_retrieval.KnowledgeRetrievalService.retrieve", fake_lexical)
    results, mode, fallback = await KnowledgeRetrievalRouterService(None).retrieve(mode="vector", fallback_to_lexical=True, query="agent", top_k=5, owner_id=None)
    assert results == [{"retrieval_mode": "lexical-v2"}]
    assert mode == "lexical-v2"
    assert fallback is True


def test_vector_provider_accepts_ollama_real_provider(monkeypatch):
    monkeypatch.setattr("app.services.knowledge.vector_retrieval.settings.embedding_provider", "ollama")
    monkeypatch.setattr("app.services.knowledge.vector_retrieval.settings.embedding_base_url", "http://localhost:11434")
    monkeypatch.setattr("app.services.knowledge.vector_retrieval.settings.embedding_model", "nomic-embed-text:latest")
    monkeypatch.setattr("app.services.knowledge.vector_retrieval.settings.embedding_dimension", 768)
    provider = VectorKnowledgeRetrievalService._build_embedding_provider()
    assert provider.__class__.__name__ == "OllamaEmbeddingProvider"
    assert provider.model == "nomic-embed-text:latest"
    assert provider.expected_dimension == 768


def test_observation_citation_targets_feed_citation_correctness():
    from app.services.retrieval_evaluation import RetrievalEvaluationCase
    cases = [RetrievalEvaluationCase("q", frozenset({"a", "b"}), frozenset({"a"}))]
    observations = [RetrievalEvaluationObservation(("b", "a"), latency_ms=12, cited_chunk_ids=("a",))]
    result = aggregate_observations(cases, observations, k=2)
    assert result["recall_at_k"] == 1.0
    assert result["precision_at_k"] == 1.0
    assert result["citation_correctness"] == 1.0
