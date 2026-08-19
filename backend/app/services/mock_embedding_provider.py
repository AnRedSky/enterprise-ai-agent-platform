from __future__ import annotations

import hashlib
import math
import re
from typing import Sequence

from app.services.embedding_provider import EmbeddingProviderError


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Build deterministic lexical-semantic features for offline evaluation.

    English identifiers/words remain whole tokens. Chinese runs additionally
    emit overlapping bigrams so a short Chinese query such as ``报销规则`` can
    match a longer sentence such as ``报销规则规定...``. This is intentionally
    a deterministic fixture strategy, not a substitute for a real embedding
    model.
    """
    tokens: list[str] = []
    for part in _TOKEN_PATTERN.findall(text.lower()):
        tokens.append(part)
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            tokens.extend(part[index : index + 2] for index in range(len(part) - 1))
    return tokens


class MockEmbeddingProvider:
    """Deterministic local embedding adapter for offline retrieval validation.

    Shared lexical features contribute to shared vector dimensions, so related
    evaluation queries and chunks can be ranked deterministically. Chinese
    text uses character bigram features to avoid treating an entire sentence
    as one token. It must not be used as evidence of real model semantic
    quality.
    """

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
