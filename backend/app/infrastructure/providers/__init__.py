"""外部 Provider 技术适配包。

模块职责：集中承载模型、Embedding、向量后端与企业集成 HTTP Provider 的具体技术适配。
边界：不放领域业务规则；同一外部能力只保留一个正式技术实现，Service 只依赖稳定 Contract。
关键外部依赖：各具体 Provider 适配及其第三方 SDK/HTTP 客户端。
"""

from .embedding import EmbeddingProvider, EmbeddingProviderError, OpenAICompatibleEmbeddingProvider
from .mock_embedding import MockEmbeddingProvider
from .mock_model import MockModelProvider
from .model import ModelProvider, ModelResult, ModelUsage
from .ollama_embedding import OllamaEmbeddingProvider
from .openai_model import OpenAICompatibleProvider
from .vector_retrieval import (
    InMemoryVectorRetrievalProvider,
    PgVectorRetrievalProvider,
    VectorRecord,
    VectorRetrievalProvider,
    VectorRetrievalProviderError,
    VectorSearchResult,
)
from .webhook import WebhookProvider, WebhookRequest

__all__ = [
    "EmbeddingProvider",
    "EmbeddingProviderError",
    "OpenAICompatibleEmbeddingProvider",
    "MockEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "ModelProvider",
    "ModelResult",
    "ModelUsage",
    "OpenAICompatibleProvider",
    "MockModelProvider",
    "InMemoryVectorRetrievalProvider",
    "PgVectorRetrievalProvider",
    "VectorRecord",
    "VectorRetrievalProvider",
    "VectorRetrievalProviderError",
    "VectorSearchResult",
    "WebhookProvider",
    "WebhookRequest",
]
