from __future__ import annotations

from scripts.check_knowledge_retrieval_quality import compare_quality


def _result(**overrides: object) -> dict:
    result = {
        "mode": "lexical-v2",
        "case_count": 1,
        "recall_at_k": 1.0,
        "precision_at_k": 0.5,
        "mrr": 1.0,
        "cases": [
            {
                "query": "q",
                "metrics": {
                    "recall_at_k": 1.0,
                    "precision_at_k": 0.5,
                    "mrr": 1.0,
                },
            }
        ],
    }
    result.update(overrides)
    return result


def test_quality_gate_accepts_equal_baseline() -> None:
    baseline = _result()
    assert compare_quality(_result(), baseline) == []


def test_quality_gate_rejects_aggregate_regression() -> None:
    baseline = _result()
    current = _result(precision_at_k=0.49)
    violations = compare_quality(current, baseline)
    assert any("precision_at_k regressed" in item for item in violations)


def test_quality_gate_rejects_case_regression() -> None:
    baseline = _result()
    current = _result(
        cases=[
            {
                "query": "q",
                "metrics": {
                    "recall_at_k": 1.0,
                    "precision_at_k": 0.5,
                    "mrr": 0.5,
                },
            }
        ]
    )
    violations = compare_quality(current, baseline)
    assert any("case 'q' mrr regressed" in item for item in violations)


def test_quality_gate_rejects_case_set_change() -> None:
    baseline = _result()
    current = _result(cases=[])
    violations = compare_quality(current, baseline)
    assert "evaluation case queries changed" in violations
