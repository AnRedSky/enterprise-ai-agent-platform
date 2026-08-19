from __future__ import annotations

from scripts.evaluate_knowledge_retrieval_baseline import evaluate, load_cases, load_corpus, rank_case


def test_real_lexical_v2_runner_uses_corpus_and_dataset() -> None:
    cases = load_cases()
    corpus = load_corpus()

    assert len(cases) == 5
    assert len(corpus) >= 5

    ranking = rank_case(cases[0].query, corpus)
    assert ranking[0] == "chunk-fastapi-runtime"


def test_real_lexical_v2_evaluation_has_expected_retrieval_contract() -> None:
    result = evaluate()

    assert result["mode"] == "lexical-v2"
    assert result["case_count"] == 5
    assert len(result["cases"]) == result["case_count"]
    assert 0 <= result["recall_at_k"] <= 1
    assert 0 <= result["precision_at_k"] <= 1
    assert 0 <= result["mrr"] <= 1
    assert result["mrr"] == 1.0
