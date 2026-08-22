from app.services.retrieval_evaluation import (
    RetrievalEvaluationCase,
    RetrievalEvaluationObservation,
    aggregate_evaluation,
    aggregate_observations,
    citation_correctness,
    evaluate_case,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_precision_and_mrr_are_deterministic():
    retrieved = ["a", "b", "c"]
    relevant = {"b", "c"}
    assert recall_at_k(retrieved, relevant, 3) == 1.0
    assert precision_at_k(retrieved, relevant, 3) == 2 / 3
    assert reciprocal_rank(retrieved, relevant) == 0.5


def test_evaluate_case_returns_bounded_metrics():
    case = RetrievalEvaluationCase("报销规则", frozenset({"expense-1"}))
    metrics = evaluate_case(case, ["noise", "expense-1"], k=3)
    assert metrics == {
        "recall_at_k": 1.0,
        "precision_at_k": 0.5,
        "mrr": 0.5,
        "citation_correctness": 0.5,
    }


def test_evaluate_case_supports_explicit_citation_targets():
    case = RetrievalEvaluationCase(
        "q",
        frozenset({"a", "b"}),
        frozenset({"a"}),
    )
    metrics = evaluate_case(case, ["a", "b"], k=2, cited_targets=["a"])
    assert metrics["citation_correctness"] == 1.0


def test_citation_correctness_requires_retrieved_and_expected_target():
    assert citation_correctness(["a"], ["a", "noise"], {"a"}) == 1.0
    assert citation_correctness(["a"], ["noise"], {"a"}) == 0.0
    assert citation_correctness(["noise"], ["noise"], {"a"}) == 0.0
    assert citation_correctness([], ["a"], {"a"}) == 0.0


def test_aggregate_evaluation_averages_cases():
    cases = [
        RetrievalEvaluationCase("q1", frozenset({"a"})),
        RetrievalEvaluationCase("q2", frozenset({"b"})),
    ]
    rankings = [["a"], ["noise", "b"]]
    result = aggregate_evaluation(cases, rankings, k=2)
    assert result == {
        "cases": 2,
        "recall_at_k": 1.0,
        "precision_at_k": 0.75,
        "mrr": 0.75,
        "citation_correctness": 0.75,
    }


def test_aggregate_evaluation_rejects_mismatched_inputs():
    case = RetrievalEvaluationCase("q1", frozenset({"a"}))
    try:
        aggregate_evaluation([case], [], k=3)
    except ValueError as exc:
        assert "same length" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_aggregate_observations_reports_quality_latency_and_errors():
    cases = [
        RetrievalEvaluationCase("q1", frozenset({"a"})),
        RetrievalEvaluationCase("q2", frozenset({"b"})),
        RetrievalEvaluationCase("q3", frozenset({"c"})),
    ]
    observations = [
        RetrievalEvaluationObservation(("a",), latency_ms=10),
        RetrievalEvaluationObservation(("noise", "b"), latency_ms=20),
        RetrievalEvaluationObservation((), latency_ms=30, error="provider unavailable"),
    ]
    result = aggregate_observations(cases, observations, k=2)
    assert result == {
        "cases": 3,
        "successful_cases": 2,
        "error_cases": 1,
        "error_rate": 0.333333,
        "recall_at_k": 1.0,
        "precision_at_k": 0.75,
        "mrr": 0.75,
        "citation_correctness": 0.75,
        "avg_latency_ms": 20.0,
    }


def test_aggregate_observations_rejects_mismatched_inputs():
    case = RetrievalEvaluationCase("q1", frozenset({"a"}))
    try:
        aggregate_observations([case], [])
    except ValueError as exc:
        assert "same length" in str(exc)
    else:
        raise AssertionError("expected ValueError")
