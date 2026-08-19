from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    query: str
    relevant_chunk_ids: frozenset[str]


@dataclass(frozen=True)
class RetrievalEvaluationObservation:
    """One measured retrieval execution used by the offline quality gate."""

    retrieved_chunk_ids: tuple[str, ...]
    latency_ms: float = 0.0
    error: str | None = None


def recall_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    if k < 1:
        raise ValueError("k must be greater than zero")
    if not relevant:
        return 1.0
    hits = len(set(retrieved[:k]) & relevant)
    return hits / len(relevant)


def precision_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    if k < 1:
        raise ValueError("k must be greater than zero")
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


def aggregate_evaluation(
    cases: Sequence[RetrievalEvaluationCase],
    rankings: Sequence[Sequence[str]],
    k: int = 3,
) -> dict[str, float | int]:
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


def aggregate_observations(
    cases: Sequence[RetrievalEvaluationCase],
    observations: Sequence[RetrievalEvaluationObservation],
    k: int = 3,
) -> dict[str, float | int]:
    """Aggregate quality, latency and provider-error measurements.

    Errors remain visible in the report and are excluded from ranking-quality
    averages because there is no valid ranking to score. The error rate is
    still reported so a provider cannot hide availability failures behind
    quality metrics.
    """

    if len(cases) != len(observations):
        raise ValueError("cases and observations must have the same length")
    if not cases:
        return {
            "cases": 0,
            "successful_cases": 0,
            "error_cases": 0,
            "error_rate": 0.0,
            "recall_at_k": 0.0,
            "precision_at_k": 0.0,
            "mrr": 0.0,
            "avg_latency_ms": 0.0,
        }

    successful = [
        (case, observation)
        for case, observation in zip(cases, observations)
        if not observation.error
    ]
    metrics = [
        evaluate_case(case, observation.retrieved_chunk_ids, k)
        for case, observation in successful
    ]
    count = len(cases)
    success_count = len(successful)
    error_count = count - success_count

    return {
        "cases": count,
        "successful_cases": success_count,
        "error_cases": error_count,
        "error_rate": round(error_count / count, 6),
        "recall_at_k": round(sum(item["recall_at_k"] for item in metrics) / success_count, 6) if metrics else 0.0,
        "precision_at_k": round(sum(item["precision_at_k"] for item in metrics) / success_count, 6) if metrics else 0.0,
        "mrr": round(sum(item["mrr"] for item in metrics) / success_count, 6) if metrics else 0.0,
        "avg_latency_ms": round(sum(item.latency_ms for _, item in zip(cases, observations)) / count, 3),
    }
