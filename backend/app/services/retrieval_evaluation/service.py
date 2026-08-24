"""Retrieval Evaluation 核心指标与观测聚合模块。

职责：定义评估 Case/Observation，并计算 recall、precision、MRR、引用正确性及错误率等离线指标。
边界：只计算已提供的检索结果，不负责检索、Embedding 或生产数据访问。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    query: str
    relevant_chunk_ids: frozenset[str]
    expected_citation_targets: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RetrievalEvaluationObservation:
    """用于离线质量门禁的一次检索观测结果。"""

    retrieved_chunk_ids: tuple[str, ...]
    latency_ms: float = 0.0
    error: str | None = None
    cited_chunk_ids: tuple[str, ...] | None = None


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


def citation_correctness(
    cited_targets: Sequence[str],
    retrieved: Sequence[str],
    expected_targets: set[str],
) -> float:
    """计算引用目标是否来自检索结果且属于预期目标。"""

    if not cited_targets:
        return 0.0
    retrieved_set = set(retrieved)
    correct = sum(
        1
        for target in cited_targets
        if target in retrieved_set and target in expected_targets
    )
    return correct / len(cited_targets)


def evaluate_case(
    case: RetrievalEvaluationCase,
    retrieved: Sequence[str],
    k: int = 3,
    cited_targets: Sequence[str] | None = None,
) -> dict[str, float]:
    relevant = set(case.relevant_chunk_ids)
    citations = list(retrieved if cited_targets is None else cited_targets)
    expected_targets = set(case.expected_citation_targets or case.relevant_chunk_ids)
    return {
        "recall_at_k": round(recall_at_k(retrieved, relevant, k), 6),
        "precision_at_k": round(precision_at_k(retrieved, relevant, k), 6),
        "mrr": round(reciprocal_rank(retrieved, relevant), 6),
        "citation_correctness": round(
            citation_correctness(citations, retrieved, expected_targets), 6
        ),
    }


def aggregate_evaluation(
    cases: Sequence[RetrievalEvaluationCase],
    rankings: Sequence[Sequence[str]],
    k: int = 3,
) -> dict[str, float | int]:
    if len(cases) != len(rankings):
        raise ValueError("cases and rankings must have the same length")
    if not cases:
        return {
            "cases": 0,
            "recall_at_k": 0.0,
            "precision_at_k": 0.0,
            "mrr": 0.0,
            "citation_correctness": 0.0,
        }

    metrics = [evaluate_case(case, ranking, k) for case, ranking in zip(cases, rankings)]
    count = len(metrics)
    return {
        "cases": count,
        "recall_at_k": round(sum(item["recall_at_k"] for item in metrics) / count, 6),
        "precision_at_k": round(sum(item["precision_at_k"] for item in metrics) / count, 6),
        "mrr": round(sum(item["mrr"] for item in metrics) / count, 6),
        "citation_correctness": round(
            sum(item["citation_correctness"] for item in metrics) / count, 6
        ),
    }


def aggregate_observations(
    cases: Sequence[RetrievalEvaluationCase],
    observations: Sequence[RetrievalEvaluationObservation],
    k: int = 3,
) -> dict[str, float | int]:
    """聚合质量、延迟、引用和 Provider 错误率观测。"""

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
            "citation_correctness": 0.0,
            "avg_latency_ms": 0.0,
        }

    successful = [
        (case, observation)
        for case, observation in zip(cases, observations)
        if not observation.error
    ]
    metrics = [
        evaluate_case(
            case,
            observation.retrieved_chunk_ids,
            k,
            cited_targets=observation.cited_chunk_ids,
        )
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
        "citation_correctness": round(
            sum(item["citation_correctness"] for item in metrics) / success_count, 6
        ) if metrics else 0.0,
        "avg_latency_ms": round(sum(item.latency_ms for _, item in zip(cases, observations)) / count, 3),
    }
