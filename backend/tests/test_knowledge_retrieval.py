from app.services.knowledge_retrieval import KnowledgeRetrievalService


def test_retrieval_score_is_deterministic_and_bounded():
    service = KnowledgeRetrievalService(None)
    score = service._score("FastAPI Agent", "FastAPI Agent Runtime")
    assert score == 1.0
    assert 0 <= score <= 1
    assert score == service._score("FastAPI Agent", "FastAPI Agent Runtime")


def test_retrieval_score_ignores_non_matching_chunks():
    service = KnowledgeRetrievalService(None)
    assert service._score("PostgreSQL", "Vue Agent Runtime") == 0.0


def test_retrieval_tokens_support_chinese_and_ascii_terms():
    tokens = KnowledgeRetrievalService._tokens("企业级 Agent Runtime")
    assert "企业级" in tokens
    assert "agent" in tokens
    assert "runtime" in tokens
