from app.services.retrieval_evaluation import (
    RetrievalEvaluationCase,
    aggregate_evaluation,
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
    assert metrics == {"recall_at_k": 1.0, "precision_at_k": 0.5, "mrr": 0.5}


def test_aggregate_evaluation_averages_cases():
    cases = [
        RetrievalEvaluationCase("q1", frozenset({"a"})),
        RetrievalEvaluationCase("q2", frozenset({"b"})),
    ]
    rankings = [["a"], ["noise", "b"]]
    result = aggregate_evaluation(cases, rankings, k=2)
    assert result == {"cases": 2, "recall_at_k": 1.0, "precision_at_k": 0.75, "mrr": 0.75}


def test_aggregate_evaluation_rejects_mismatched_inputs():
    case = RetrievalEvaluationCase("q1", frozenset({"a"}))
    try:
        aggregate_evaluation([case], [], k=3)
    except ValueError as exc:
        assert "same length" in str(exc)
    else:
        raise AssertionError("expected ValueError")
