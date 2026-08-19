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
    assert "企业" in tokens
    assert "agent" in tokens
    assert "runtime" in tokens


def test_chinese_phrase_retrieval_matches_embedded_phrase():
    service = KnowledgeRetrievalService(None)
    assert service._score("报销规则", "公司的报销规则与审批流程") > 0


def test_score_details_returns_matched_terms():
    service = KnowledgeRetrievalService(None)
    score, matched = service._score_details("FastAPI Agent", "FastAPI Agent Runtime")
    assert score == 1.0
    assert "fastapi" in matched
    assert "agent" in matched


def test_retrieval_policy_is_explicit_and_bounded():
    service = KnowledgeRetrievalService(None)
    assert service.RETRIEVAL_MODE == "lexical-v2"
    assert service.MAX_CANDIDATES == 5000
    assert 0 <= service.DEFAULT_MIN_SCORE <= 1
