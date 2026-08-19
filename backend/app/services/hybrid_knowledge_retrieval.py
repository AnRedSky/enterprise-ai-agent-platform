from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


class HybridRetrievalError(ValueError):
    """Raised when hybrid retrieval inputs violate the provider-neutral contract."""


@dataclass(frozen=True)
class HybridCandidate:
    """Provider-neutral candidate used to fuse lexical and vector rankings."""

    chunk_id: str
    score: float
    source: str
    payload: dict


@dataclass(frozen=True)
class HybridRetrievalConfig:
    """Stable score-fusion configuration for the first hybrid implementation."""

    lexical_weight: float = 0.5
    vector_weight: float = 0.5

    def __post_init__(self) -> None:
        if self.lexical_weight < 0 or self.vector_weight < 0:
            raise HybridRetrievalError("hybrid weights must not be negative")
        if self.lexical_weight + self.vector_weight <= 0:
            raise HybridRetrievalError("at least one hybrid weight must be greater than zero")


class HybridRetrievalService:
    """Fuse lexical-v2 and vector candidates without exposing provider details.

    Both upstream contracts expose normalized scores in the range 0..1. When a
    chunk is returned by both sources, its score is the configured weighted
    fusion of the two normalized scores. A chunk returned by only one source
    keeps that source's normalized score rather than being penalized merely for
    missing from the other candidate set. This keeps single-source candidates
    comparable with their originating retrieval signal while still rewarding
    candidates supported by both sources.

    Ties are resolved by chunk_id so ranking remains stable across database
    execution order. Reranking/model-based fusion is intentionally deferred to
    the next phase.
    """

    RETRIEVAL_MODE = "hybrid"

    def __init__(self, config: HybridRetrievalConfig | None = None):
        self.config = config or HybridRetrievalConfig()

    def fuse(
        self,
        lexical: Sequence[HybridCandidate],
        vector: Sequence[HybridCandidate],
        top_k: int,
    ) -> list[HybridCandidate]:
        if top_k < 1:
            raise HybridRetrievalError("top_k must be greater than zero")

        candidates: dict[str, HybridCandidate] = {}
        lexical_scores: dict[str, float] = {}
        vector_scores: dict[str, float] = {}

        for candidate in lexical:
            self._validate_candidate(candidate)
            lexical_scores[candidate.chunk_id] = max(
                lexical_scores.get(candidate.chunk_id, 0.0), candidate.score
            )
            candidates.setdefault(candidate.chunk_id, candidate)

        for candidate in vector:
            self._validate_candidate(candidate)
            vector_scores[candidate.chunk_id] = max(
                vector_scores.get(candidate.chunk_id, 0.0), candidate.score
            )
            candidates.setdefault(candidate.chunk_id, candidate)

        weight_total = self.config.lexical_weight + self.config.vector_weight
        fused: list[HybridCandidate] = []
        for chunk_id, candidate in candidates.items():
            lexical_score = lexical_scores.get(chunk_id)
            vector_score = vector_scores.get(chunk_id)

            if lexical_score is not None and vector_score is not None:
                score = (
                    self.config.lexical_weight * lexical_score
                    + self.config.vector_weight * vector_score
                ) / weight_total
            elif lexical_score is not None:
                score = lexical_score
            else:
                # Every candidate is guaranteed to come from at least one source.
                score = vector_score  # type: ignore[assignment]

            source_parts: list[str] = []
            if lexical_score is not None:
                source_parts.append("lexical")
            if vector_score is not None:
                source_parts.append("vector")
            fused.append(
                HybridCandidate(
                    chunk_id=chunk_id,
                    score=round(score, 6),
                    source="+".join(source_parts),
                    payload=candidate.payload,
                )
            )

        fused.sort(key=lambda item: (-item.score, item.chunk_id))
        return fused[:top_k]

    @staticmethod
    def _validate_candidate(candidate: HybridCandidate) -> None:
        if not candidate.chunk_id:
            raise HybridRetrievalError("chunk_id must not be empty")
        if not 0 <= candidate.score <= 1:
            raise HybridRetrievalError("candidate score must be between 0 and 1")
