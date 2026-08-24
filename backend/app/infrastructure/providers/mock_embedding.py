"""离线 Embedding 测试适配器。

职责：提供确定性的本地向量实现，用于离线检索验证和单元测试。
边界：仅承担测试用 Provider 技术适配，不代表真实模型语义质量，也不参与生产 Provider 路由。
关键依赖：Python hashlib、math、re 标准库，以及统一 EmbeddingProviderError。
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Sequence

from .embedding import EmbeddingProviderError


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Build deterministic lexical-semantic features for offline evaluation."""
    tokens: list[str] = []
    for part in _TOKEN_PATTERN.findall(text.lower()):
        tokens.append(part)
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            tokens.extend(part[index : index + 2] for index in range(len(part) - 1))
    return tokens


class MockEmbeddingProvider:
    """Deterministic local embedding adapter for offline retrieval validation."""

    def __init__(self, dimension: int = 1536) -> None:
        if dimension <= 0:
            raise ValueError("embedding dimension must be positive")
        self.dimension = dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise EmbeddingProviderError("embedding texts must not contain empty values")
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = _tokenize(text)
        if not tokens:
            raise EmbeddingProviderError("embedding text must contain searchable content")

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimension
            sign = 1.0 if digest[8] & 1 else -1.0
            weight = 1.0 + (digest[9] / 255.0) * 0.25
            vector[index] += sign * weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            raise EmbeddingProviderError("failed to construct non-zero mock embedding")
        return [value / norm for value in vector]
