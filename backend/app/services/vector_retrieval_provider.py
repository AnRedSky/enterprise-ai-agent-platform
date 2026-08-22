from __future__ import annotations

import json
from dataclasses import dataclass
from math import sqrt
from typing import Protocol, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class VectorRetrievalProviderError(RuntimeError):
    """Raised when a vector retrieval provider cannot satisfy its contract."""


@dataclass(frozen=True)
class VectorRecord:
    """Provider-neutral vector record used by retrieval adapters."""

    chunk_id: str
    embedding: tuple[float, ...]
    metadata: dict[str, str]


@dataclass(frozen=True)
class VectorSearchResult:
    """Provider-neutral vector search result."""

    chunk_id: str
    score: float
    metadata: dict[str, str]


class VectorRetrievalProvider(Protocol):
    """Contract implemented by pgvector, Milvus, or another vector backend."""

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        ...

    async def search(
        self,
        query_embedding: Sequence[float],
        top_k: int,
        min_score: float = 0.0,
        knowledge_base_id: str | None = None,
    ) -> list[VectorSearchResult]:
        ...


class InMemoryVectorRetrievalProvider:
    """Deterministic local adapter for contract tests before a real Vector DB."""

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        for record in records:
            if not record.embedding:
                raise VectorRetrievalProviderError("embedding must not be empty")
            if not all(isinstance(value, (int, float)) for value in record.embedding):
                raise VectorRetrievalProviderError("embedding vector contains a non-numeric value")
            self._records[record.chunk_id] = record

    async def search(
        self,
        query_embedding: Sequence[float],
        top_k: int,
        min_score: float = 0.0,
        knowledge_base_id: str | None = None,
    ) -> list[VectorSearchResult]:
        if not query_embedding:
            raise VectorRetrievalProviderError("query embedding must not be empty")
        if top_k < 1:
            raise VectorRetrievalProviderError("top_k must be greater than zero")
        if not 0 <= min_score <= 1:
            raise VectorRetrievalProviderError("min_score must be between 0 and 1")

        query = tuple(float(value) for value in query_embedding)
        results: list[VectorSearchResult] = []
        for record in self._records.values():
            if knowledge_base_id is not None and record.metadata.get("knowledge_base_id") != knowledge_base_id:
                continue
            if len(record.embedding) != len(query):
                raise VectorRetrievalProviderError("embedding dimensions must match")
            score = self._cosine_similarity(query, record.embedding)
            if score >= min_score:
                results.append(
                    VectorSearchResult(
                        chunk_id=record.chunk_id,
                        score=round(score, 6),
                        metadata=record.metadata,
                    )
                )

        results.sort(key=lambda item: (-item.score, item.chunk_id))
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (left_norm * right_norm)))


class PgVectorRetrievalProvider:
    """PostgreSQL + pgvector adapter behind the provider-neutral contract.

    Production knowledge vectors remain in the fixed-dimension ``knowledge_chunks``
    contract. Evaluation vectors are isolated in ``retrieval_evaluation_vectors``;
    that table intentionally uses pgvector's variable-dimension ``vector`` type and
    stores the governed profile dimension beside each vector. This lets each
    Embedding Profile validate against its own dimension without changing the
    production storage contract or mixing vector spaces.
    """

    TABLE = "knowledge_chunks"
    EVALUATION_TABLE = "retrieval_evaluation_vectors"

    def __init__(self, db: AsyncSession, embedding_dimension: int) -> None:
        if embedding_dimension < 1:
            raise VectorRetrievalProviderError("embedding_dimension must be greater than zero")
        self.db = db
        self.embedding_dimension = embedding_dimension

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        evaluation = any("evaluation_chunk_id" in record.metadata for record in records)
        table = self.EVALUATION_TABLE if evaluation else self.TABLE
        for record in records:
            self._validate_embedding(record.embedding)
            knowledge_base_id = record.metadata.get("knowledge_base_id")
            document_version_id = record.metadata.get("document_version_id")
            if not knowledge_base_id:
                raise VectorRetrievalProviderError("pgvector record metadata requires knowledge_base_id")

            if evaluation:
                await self.db.execute(
                    text(
                        f"""
                        INSERT INTO {table}
                            (chunk_id, knowledge_base_id, embedding_dimension, embedding, metadata)
                        VALUES
                            (:chunk_id, CAST(:knowledge_base_id AS uuid), :embedding_dimension,
                             CAST(:embedding AS vector), CAST(:metadata AS jsonb))
                        ON CONFLICT (knowledge_base_id, embedding_dimension, chunk_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            updated_at = CURRENT_TIMESTAMP
                        """
                    ),
                    {
                        "chunk_id": record.chunk_id,
                        "knowledge_base_id": knowledge_base_id,
                        "embedding_dimension": self.embedding_dimension,
                        "embedding": self._vector_literal(record.embedding),
                        "metadata": json.dumps(record.metadata),
                    },
                )
                continue

            document_version_id = record.metadata.get("document_version_id")
            if not document_version_id:
                raise VectorRetrievalProviderError(
                    "pgvector record metadata requires knowledge_base_id and document_version_id"
                )
            await self.db.execute(
                text(
                    f"""
                    INSERT INTO {table}
                        (chunk_id, knowledge_base_id, document_version_id, embedding, metadata)
                    VALUES
                        (:chunk_id, CAST(:knowledge_base_id AS uuid), CAST(:document_version_id AS uuid),
                         CAST(:embedding AS vector), CAST(:metadata AS jsonb))
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        knowledge_base_id = EXCLUDED.knowledge_base_id,
                        document_version_id = EXCLUDED.document_version_id,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "chunk_id": record.chunk_id,
                    "knowledge_base_id": knowledge_base_id,
                    "document_version_id": document_version_id,
                    "embedding": self._vector_literal(record.embedding),
                    "metadata": json.dumps(record.metadata),
                },
            )
        await self.db.commit()

    async def search(
        self,
        query_embedding: Sequence[float],
        top_k: int,
        min_score: float = 0.0,
        knowledge_base_id: str | None = None,
    ) -> list[VectorSearchResult]:
        if top_k < 1:
            raise VectorRetrievalProviderError("top_k must be greater than zero")
        if not 0 <= min_score <= 1:
            raise VectorRetrievalProviderError("min_score must be between 0 and 1")
        self._validate_embedding(query_embedding)

        evaluation_scope = await self._has_evaluation_vectors(knowledge_base_id)
        if evaluation_scope:
            result = await self.db.execute(
                text(
                    f"""
                    SELECT chunk_id::text AS chunk_id,
                           1 - (embedding <=> CAST(:embedding AS vector)) AS score,
                           metadata
                    FROM {self.EVALUATION_TABLE}
                    WHERE (CAST(:knowledge_base_id AS uuid) IS NULL OR knowledge_base_id = CAST(:knowledge_base_id AS uuid))
                      AND embedding_dimension = :embedding_dimension
                      AND 1 - (embedding <=> CAST(:embedding AS vector)) >= :min_score
                    ORDER BY embedding <=> CAST(:embedding AS vector) ASC, chunk_id ASC
                    LIMIT :top_k
                    """
                ),
                {
                    "embedding": self._vector_literal(query_embedding),
                    "knowledge_base_id": knowledge_base_id,
                    "embedding_dimension": self.embedding_dimension,
                    "min_score": min_score,
                    "top_k": top_k,
                },
            )
        else:
            result = await self.db.execute(
                text(
                    f"""
                    SELECT chunk_id::text AS chunk_id,
                           1 - (embedding <=> CAST(:embedding AS vector)) AS score,
                           metadata
                    FROM {self.TABLE}
                    WHERE (CAST(:knowledge_base_id AS uuid) IS NULL OR knowledge_base_id = CAST(:knowledge_base_id AS uuid))
                      AND 1 - (embedding <=> CAST(:embedding AS vector)) >= :min_score
                    ORDER BY embedding <=> CAST(:embedding AS vector) ASC, chunk_id ASC
                    LIMIT :top_k
                    """
                ),
                {
                    "embedding": self._vector_literal(query_embedding),
                    "knowledge_base_id": knowledge_base_id,
                    "min_score": min_score,
                    "top_k": top_k,
                },
            )
        return [
            VectorSearchResult(
                chunk_id=str(row.chunk_id),
                score=round(float(row.score), 6),
                metadata=dict(row.metadata or {}),
            )
            for row in result.fetchall()
        ]

    async def _has_evaluation_vectors(self, knowledge_base_id: str | None) -> bool:
        if knowledge_base_id is None:
            return False
        result = await self.db.execute(
            text(
                f"""
                SELECT EXISTS(
                    SELECT 1
                    FROM {self.EVALUATION_TABLE}
                    WHERE knowledge_base_id = CAST(:knowledge_base_id AS uuid)
                      AND embedding_dimension = :embedding_dimension
                )
                """
            ),
            {
                "knowledge_base_id": knowledge_base_id,
                "embedding_dimension": self.embedding_dimension,
            },
        )
        return bool(result.scalar())

    def _validate_embedding(self, embedding: Sequence[float]) -> None:
        if not embedding:
            raise VectorRetrievalProviderError("embedding must not be empty")
        if len(embedding) != self.embedding_dimension:
            raise VectorRetrievalProviderError(
                f"embedding dimensions must match configured dimension {self.embedding_dimension}"
            )
        if not all(isinstance(value, (int, float)) for value in embedding):
            raise VectorRetrievalProviderError("embedding vector contains a non-numeric value")

    @staticmethod
    def _vector_literal(embedding: Sequence[float]) -> str:
        return "[" + ",".join(str(float(value)) for value in embedding) + "]"
