"""Knowledge 混合检索领域服务。

职责：负责合并 Knowledge 领域已有的词法召回与向量召回候选，并按配置执行确定性的加权融合、排序、去重与评分明细记录。
边界：只负责检索候选融合与评分，不实现词法检索、Embedding 生成、向量数据库访问、Provider 适配或 API 协议转换；具体召回能力由同领域的 lexical/vector 服务提供。
关键依赖：HybridCandidate 数据契约，以及上层传入的词法/向量候选序列。
"""

from dataclasses import dataclass
from typing import Sequence


class HybridRetrievalError(ValueError):
    pass


@dataclass(frozen=True)
class HybridCandidate:
    chunk_id: str
    score: float
    source: str
    payload: dict


@dataclass(frozen=True)
class HybridRetrievalConfig:
    lexical_weight: float = 0.5
    vector_weight: float = 0.5

    def __post_init__(self) -> None:
        if self.lexical_weight < 0 or self.vector_weight < 0:
            raise HybridRetrievalError("hybrid weights must not be negative")
        if self.lexical_weight + self.vector_weight <= 0:
            raise HybridRetrievalError("at least one hybrid weight must be greater than zero")


class HybridRetrievalService:
    """Provider-neutral fusion service for already retrieved Knowledge candidates."""

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
        candidates = {}
        lexical_scores = {}
        vector_scores = {}
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
        total = self.config.lexical_weight + self.config.vector_weight
        fused = []
        for chunk_id, candidate in candidates.items():
            left = lexical_scores.get(chunk_id)
            right = vector_scores.get(chunk_id)
            if left is not None and right is not None:
                score = (
                    self.config.lexical_weight * left
                    + self.config.vector_weight * right
                ) / total
            elif left is not None:
                score = left
            else:
                score = right
            sources = (["lexical"] if left is not None else []) + (
                ["vector"] if right is not None else []
            )
            payload = dict(candidate.payload)
            payload["hybrid_score_breakdown"] = {
                "lexical_score": left,
                "vector_score": right,
                "lexical_weight": self.config.lexical_weight,
                "vector_weight": self.config.vector_weight,
                "fused_score": round(score, 6),
                "support": sources,
            }
            fused.append(
                HybridCandidate(
                    chunk_id, round(score, 6), "+".join(sources), payload
                )
            )
        fused.sort(
            key=lambda item: (
                -(1 if item.source == "lexical+vector" else 0),
                -item.score,
                item.chunk_id,
            )
        )
        return fused[:top_k]

    @staticmethod
    def _validate_candidate(candidate: HybridCandidate) -> None:
        if not candidate.chunk_id:
            raise HybridRetrievalError("chunk_id must not be empty")
        if not 0 <= candidate.score <= 1:
            raise HybridRetrievalError("candidate score must be between 0 and 1")
