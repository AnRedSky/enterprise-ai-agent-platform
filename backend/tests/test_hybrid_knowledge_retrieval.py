import pytest

from app.services.hybrid_knowledge_retrieval import (
    HybridCandidate,
    HybridRetrievalConfig,
    HybridRetrievalError,
    HybridRetrievalService,
)


def candidate(chunk_id: str, score: float, source: str) -> HybridCandidate:
    return HybridCandidate(chunk_id=chunk_id, score=score, source=source, payload={"chunk_id": chunk_id})


def test_weighted_fusion_combines_candidates_and_preserves_stable_order():
    service = HybridRetrievalService(HybridRetrievalConfig(lexical_weight=0.4, vector_weight=0.6))

    results = service.fuse(
        lexical=[candidate("chunk-a", 1.0, "lexical"), candidate("chunk-b", 0.5, "lexical")],
        vector=[candidate("chunk-b", 1.0, "vector"), candidate("chunk-c", 0.8, "vector")],
        top_k=3,
    )

    assert [item.chunk_id for item in results] == ["chunk-b", "chunk-a", "chunk-c"]
    assert results[0].score == 0.8
    assert results[0].source == "lexical+vector"


def test_duplicate_candidate_from_one_source_uses_highest_score():
    service = HybridRetrievalService()

    results = service.fuse(
        lexical=[candidate("chunk-a", 0.4, "lexical"), candidate("chunk-a", 0.9, "lexical")],
        vector=[],
        top_k=1,
    )

    assert results[0].score == 0.9
    assert results[0].source == "lexical"


def test_weight_validation_and_score_validation():
    with pytest.raises(HybridRetrievalError):
        HybridRetrievalConfig(lexical_weight=0, vector_weight=0)

    service = HybridRetrievalService()
    with pytest.raises(HybridRetrievalError):
        service.fuse([candidate("chunk-a", 1.1, "lexical")], [], top_k=1)

    with pytest.raises(HybridRetrievalError):
        service.fuse([], [], top_k=0)


def test_equal_scores_are_sorted_by_chunk_id():
    service = HybridRetrievalService()

    results = service.fuse(
        lexical=[candidate("chunk-z", 0.8, "lexical"), candidate("chunk-a", 0.8, "lexical")],
        vector=[],
        top_k=2,
    )

    assert [item.chunk_id for item in results] == ["chunk-a", "chunk-z"]
