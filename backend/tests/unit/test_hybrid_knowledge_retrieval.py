import pytest

from app.services.knowledge.hybrid import HybridCandidate, HybridRetrievalConfig, HybridRetrievalError, HybridRetrievalService


def candidate(chunk_id: str, score: float, source: str) -> HybridCandidate:
    return HybridCandidate(chunk_id=chunk_id, score=score, source=source, payload={"chunk_id": chunk_id})


def test_weighted_fusion_combines_candidates_and_preserves_stable_order():
    service = HybridRetrievalService(HybridRetrievalConfig(lexical_weight=0.4, vector_weight=0.6))
    results = service.fuse(lexical=[candidate("chunk-a", 1.0, "lexical"), candidate("chunk-b", 0.5, "lexical")], vector=[candidate("chunk-b", 1.0, "vector"), candidate("chunk-c", 0.8, "vector")], top_k=3)
    assert [item.chunk_id for item in results] == ["chunk-b", "chunk-a", "chunk-c"]
    assert results[0].score == 0.8
    assert results[0].source == "lexical+vector"


def test_hybrid_score_breakdown_exposes_real_source_scores_and_weights():
    service = HybridRetrievalService(HybridRetrievalConfig(lexical_weight=0.4, vector_weight=0.6))
    results = service.fuse([candidate("chunk-a", 1.0, "lexical")], [candidate("chunk-a", 0.5, "vector")], top_k=1)
    assert results[0].payload["hybrid_score_breakdown"] == {"lexical_score": 1.0, "vector_score": 0.5, "lexical_weight": 0.4, "vector_weight": 0.6, "fused_score": 0.7, "support": ["lexical", "vector"]}


def test_single_source_breakdown_keeps_missing_signal_explicit():
    results = HybridRetrievalService().fuse([candidate("chunk-a", 0.9, "lexical")], [], top_k=1)
    assert results[0].payload["hybrid_score_breakdown"]["vector_score"] is None
    assert results[0].payload["hybrid_score_breakdown"]["support"] == ["lexical"]


def test_duplicate_candidate_from_one_source_uses_highest_score():
    results = HybridRetrievalService().fuse([candidate("chunk-a", 0.4, "lexical"), candidate("chunk-a", 0.9, "lexical")], [], top_k=1)
    assert results[0].score == 0.9


def test_weight_validation_and_score_validation():
    with pytest.raises(HybridRetrievalError):
        HybridRetrievalConfig(lexical_weight=0, vector_weight=0)
    with pytest.raises(HybridRetrievalError):
        HybridRetrievalService().fuse([candidate("chunk-a", 1.1, "lexical")], [], top_k=1)
    with pytest.raises(HybridRetrievalError):
        HybridRetrievalService().fuse([], [], top_k=0)


def test_equal_scores_are_sorted_by_chunk_id():
    results = HybridRetrievalService().fuse([candidate("chunk-z", 0.8, "lexical"), candidate("chunk-a", 0.8, "lexical")], [], top_k=2)
    assert [item.chunk_id for item in results] == ["chunk-a", "chunk-z"]
