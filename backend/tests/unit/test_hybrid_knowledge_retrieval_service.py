import pytest

from app.services.knowledge.hybrid_service import HybridKnowledgeRetrievalService


@pytest.mark.asyncio
async def test_hybrid_retrieval_combines_real_service_outputs(monkeypatch):
    async def fake_lexical(self, **kwargs):
        return [{"chunk_id": "chunk-a", "relevance_score": 1.0, "retrieval_mode": "lexical-v2", "content": "A"}, {"chunk_id": "chunk-b", "relevance_score": 0.5, "retrieval_mode": "lexical-v2", "content": "B"}]
    async def fake_vector(self, **kwargs):
        return [{"chunk_id": "chunk-b", "relevance_score": 1.0, "retrieval_mode": "vector", "content": "B"}, {"chunk_id": "chunk-c", "relevance_score": 0.8, "retrieval_mode": "vector", "content": "C"}]
    monkeypatch.setattr("app.services.knowledge.hybrid_service.KnowledgeRetrievalService.retrieve", fake_lexical)
    monkeypatch.setattr("app.services.knowledge.hybrid_service.VectorKnowledgeRetrievalService.retrieve", fake_vector)
    results = await HybridKnowledgeRetrievalService(None).retrieve(query="q", top_k=3, owner_id=None, lexical_weight=0.4, vector_weight=0.6)
    assert [item["chunk_id"] for item in results] == ["chunk-b", "chunk-a", "chunk-c"]
    assert results[0]["retrieval_mode"] == "hybrid"
    assert results[0]["retrieval_sources"] == ["lexical", "vector"]
    assert results[0]["relevance_score"] == 0.8
    assert results[1]["relevance_score"] == 1.0
    assert results[2]["relevance_score"] == 0.8


@pytest.mark.asyncio
async def test_hybrid_applies_min_score_after_fusion(monkeypatch):
    async def fake_lexical(self, **kwargs):
        return [{"chunk_id": "chunk-a", "relevance_score": 0.4, "content": "A"}]
    async def fake_vector(self, **kwargs):
        return [{"chunk_id": "chunk-b", "relevance_score": 0.5, "content": "B"}]
    monkeypatch.setattr("app.services.knowledge.hybrid_service.KnowledgeRetrievalService.retrieve", fake_lexical)
    monkeypatch.setattr("app.services.knowledge.hybrid_service.VectorKnowledgeRetrievalService.retrieve", fake_vector)
    results = await HybridKnowledgeRetrievalService(None).retrieve(query="q", top_k=5, owner_id=None, min_score=0.45)
    assert [item["chunk_id"] for item in results] == ["chunk-b"]
