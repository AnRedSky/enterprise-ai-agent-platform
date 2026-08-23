"""外部 Provider 技术适配包。

所有外部模型、Embedding 与向量后端适配集中在此处，避免在业务 Service 中形成重复实现。
"""

from .embedding import EmbeddingProvider, EmbeddingProviderError, OpenAICompatibleEmbeddingProvider
from .mock_embedding import MockEmbeddingProvider
from .ollama_embedding import OllamaEmbeddingProvider
from .vector_retrieval import (
    InMemoryVectorRetrievalProvider,
    PgVectorRetrievalProvider,
    VectorRecord,
    VectorRetrievalProvider,
    VectorRetrievalProviderError,
    VectorSearchResult,
)

__all__ = [
    "EmbeddingProvider",
    "EmbeddingProviderError",
    "OpenAICompatibleEmbeddingProvider",
    "MockEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "InMemoryVectorRetrievalProvider",
    "PgVectorRetrievalProvider",
    "VectorRecord",
    "VectorRetrievalProvider",
    "VectorRetrievalProviderError",
    "VectorSearchResult",
]
