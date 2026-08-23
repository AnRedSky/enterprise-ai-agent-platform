"""Knowledge 业务领域入口。

统一导出 Knowledge 的领域服务与契约；外部技术 Provider 不在本包重复实现。
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
