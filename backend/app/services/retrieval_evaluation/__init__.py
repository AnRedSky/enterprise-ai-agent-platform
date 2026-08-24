"""Retrieval Evaluation 领域公开入口。

职责：统一离线检索质量指标、数据集、配置、baseline/regression 与运行追踪能力。
边界：仅用于离线评估，不提供生产检索结果；生产数据继续由 PostgreSQL/pgvector 等正式检索模块负责。
"""

from .baseline import (
    IDENTITY_FIELDS,
    QUALITY_METRICS,
    build_baseline,
    build_regression_report,
    compare_baseline,
    write_baseline,
)
from .config import RetrievalEvaluationConfig, config_from_settings, resolve_api_key, validate_config
from .dataset import RetrievalEvaluationDataset, load_retrieval_evaluation_dataset
from .service import (
    RetrievalEvaluationCase,
    RetrievalEvaluationObservation,
    aggregate_evaluation,
    aggregate_observations,
    citation_correctness,
    evaluate_case,
    precision_at_k,
    reciprocal_rank,
    recall_at_k,
)
from .trace import RetrievalEvaluationTraceService

__all__ = [
    "IDENTITY_FIELDS",
    "QUALITY_METRICS",
    "RetrievalEvaluationCase",
    "RetrievalEvaluationConfig",
    "RetrievalEvaluationDataset",
    "RetrievalEvaluationObservation",
    "RetrievalEvaluationTraceService",
    "aggregate_evaluation",
    "aggregate_observations",
    "build_baseline",
    "build_regression_report",
    "citation_correctness",
    "compare_baseline",
    "config_from_settings",
    "evaluate_case",
    "load_retrieval_evaluation_dataset",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
    "resolve_api_key",
    "validate_config",
    "write_baseline",
]
