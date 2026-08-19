from uuid import uuid4

from app.schemas.knowledge_retrieval import KnowledgeRetrievalRequest, KnowledgeRetrievalResponse


def test_hybrid_retrieval_request_accepts_weights_and_mode():
    payload = KnowledgeRetrievalRequest(
        query="enterprise agent",
        top_k=5,
        mode="hybrid",
        lexical_weight=0.4,
        vector_weight=0.6,
    )

    assert payload.mode == "hybrid"
    assert payload.lexical_weight == 0.4
    assert payload.vector_weight == 0.6


def test_hybrid_retrieval_request_rejects_negative_weight():
    try:
        KnowledgeRetrievalRequest(query="enterprise agent", mode="hybrid", lexical_weight=-0.1)
    except ValueError:
        return
    raise AssertionError("negative hybrid weights must be rejected by the API contract")


def test_hybrid_retrieval_response_accepts_score_breakdown_and_sources():
    response = KnowledgeRetrievalResponse.model_validate(
        {
            "query": "enterprise agent",
            "top_k": 3,
            "min_score": 0.0,
            "retrieval_mode": "hybrid",
            "results": [
                {
                    "document_id": uuid4(),
                    "document_version_id": uuid4(),
                    "chunk_id": uuid4(),
                    "chunk_index": 0,
                    "source_document": "Policy",
                    "source_uri": None,
                    "relevance_score": 0.81,
                    "citation": "Policy#0",
                    "content": "policy",
                    "matched_terms": ["policy"],
                    "retrieval_mode": "hybrid",
                    "retrieval_sources": ["lexical", "vector"],
                    "hybrid_score_breakdown": {
                        "lexical_score": 0.9,
                        "vector_score": 0.75,
                        "lexical_weight": 0.4,
                        "vector_weight": 0.6,
                        "fused_score": 0.81,
                        "support": ["lexical", "vector"],
                    },
                }
            ],
        }
    )

    result = response.results[0]
    assert result.retrieval_sources == ["lexical", "vector"]
    assert result.hybrid_score_breakdown is not None
    assert result.hybrid_score_breakdown.fused_score == 0.81
