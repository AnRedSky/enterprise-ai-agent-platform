from app.schemas.knowledge_retrieval import KnowledgeRetrievalRequest


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
