"""Knowledge 业务领域入口。

职责：统一导出知识接入、检索、向量索引、混合检索及领域契约，作为 Knowledge 领域的正式入口。
边界：只负责知识领域业务编排与契约，不实现外部 Embedding / Vector Provider；Provider 统一由 infrastructure/providers 提供。
关键依赖：Knowledge 领域子模块与 infrastructure/providers 中的外部能力适配。
"""

from .contract import EmbeddingProvider, Reranker, RetrievalCandidate, Retriever
from .hybrid import HybridCandidate, HybridRetrievalConfig, HybridRetrievalService
from .hybrid_service import HybridKnowledgeRetrievalService
from .ingestion import KnowledgeIngestionService
from .registry import KnowledgeRegistry
from .retrieval import KnowledgeRetrievalService
from .vector_indexing import KnowledgeVectorIndexingService
from .vector_retrieval import KnowledgeRetrievalRouterService, VectorKnowledgeRetrievalService

__all__ = [
    "EmbeddingProvider",
    "Reranker",
    "RetrievalCandidate",
    "Retriever",
    "HybridCandidate",
    "HybridRetrievalConfig",
    "HybridRetrievalService",
    "HybridKnowledgeRetrievalService",
    "KnowledgeIngestionService",
    "KnowledgeRegistry",
    "KnowledgeRetrievalService",
    "KnowledgeVectorIndexingService",
    "KnowledgeRetrievalRouterService",
    "VectorKnowledgeRetrievalService",
]
