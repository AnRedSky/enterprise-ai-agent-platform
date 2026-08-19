from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    query: str
    relevant_chunk_ids: frozenset[str]


def recall_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 1.0
    hits = len(set(retrieved[:k]) & relevant)
    return hits / len(relevant)


def precision_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    window = list(retrieved[:k])
    if not window:
        return 0.0
    hits = len(set(window) & relevant)
    return hits / len(window)


def reciprocal_rank(retrieved: Sequence[str], relevant: set[str]) -> float:
    for index, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in relevant:
            return 1.0 / index
    return 0.0


def evaluate_case(case: RetrievalEvaluationCase, retrieved: Sequence[str], k: int = 3) -> dict[str, float]:
    relevant = set(case.relevant_chunk_ids)
    return {
        "recall_at_k": round(recall_at_k(retrieved, relevant, k), 6),
        "precision_at_k": round(precision_at_k(retrieved, relevant, k), 6),
        "mrr": round(reciprocal_rank(retrieved, relevant), 6),
    }


def aggregate_evaluation(cases: Sequence[RetrievalEvaluationCase], rankings: Sequence[Sequence[str]], k: int = 3) -> dict[str, float | int]:
    if len(cases) != len(rankings):
        raise ValueError("cases and rankings must have the same length")
    if not cases:
        return {"cases": 0, "recall_at_k": 0.0, "precision_at_k": 0.0, "mrr": 0.0}

    metrics = [evaluate_case(case, ranking, k) for case, ranking in zip(cases, rankings)]
    count = len(metrics)
    return {
        "cases": count,
        "recall_at_k": round(sum(item["recall_at_k"] for item in metrics) / count, 6),
        "precision_at_k": round(sum(item["precision_at_k"] for item in metrics) / count, 6),
        "mrr": round(sum(item["mrr"] for item in metrics) / count, 6),
    }
