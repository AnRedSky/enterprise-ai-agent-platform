"""Retrieval Evaluation 配置模块。

职责：定义离线检索评估的 Provider、数据集、质量阈值与 baseline 配置，并执行配置校验。
边界：只负责评估运行配置，不保存 Secret，也不执行生产检索。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


@dataclass(frozen=True)
class RetrievalEvaluationConfig:
    """离线检索评估运行时的显式配置。"""

    embedding_provider: str
    embedding_base_url: str | None
    embedding_api_key: str | None
    embedding_model: str
    embedding_timeout_seconds: float
    embedding_dimension: int
    embedding_dimensions_parameter_enabled: bool
    dataset_path: Path
    fixture_path: Path
    baseline_path: Path
    top_k: int
    min_score: float
    model_profile_id: UUID | None = None
    min_recall_at_k: float | None = None
    min_precision_at_k: float | None = None
    min_mrr: float | None = None
    min_citation_correctness: float | None = None
    max_error_rate: float = 0.0


def validate_config(config: RetrievalEvaluationConfig) -> None:
    if config.embedding_provider not in {"openai-compatible", "ollama"}:
        raise ValueError("embedding_provider must be openai-compatible or ollama")
    if not config.embedding_base_url:
        raise ValueError("embedding_base_url is required")
    if not config.embedding_model:
        raise ValueError("embedding_model is required")
    if config.embedding_provider == "openai-compatible" and not config.embedding_api_key:
        raise ValueError("embedding_api_key is required for openai-compatible")
    if config.embedding_dimension < 1:
        raise ValueError("embedding_dimension must be greater than zero")
    if config.embedding_timeout_seconds <= 0:
        raise ValueError("embedding_timeout_seconds must be greater than zero")
    if config.top_k < 1:
        raise ValueError("top_k must be greater than zero")
    if config.min_score < 0:
        raise ValueError("min_score must be greater than or equal to zero")
    if not 0 <= config.max_error_rate <= 1:
        raise ValueError("max_error_rate must be between 0 and 1")
    for name in ("min_recall_at_k", "min_precision_at_k", "min_mrr", "min_citation_correctness"):
        value = getattr(config, name)
        if value is not None and not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1")


def config_from_settings(*, backend_root: Path, settings) -> RetrievalEvaluationConfig:
    return RetrievalEvaluationConfig(
        embedding_provider=settings.embedding_provider,
        embedding_base_url=settings.embedding_base_url,
        embedding_api_key=settings.embedding_api_key,
        embedding_model=settings.embedding_model or "",
        embedding_timeout_seconds=settings.embedding_timeout_seconds,
        embedding_dimension=settings.embedding_dimension,
        embedding_dimensions_parameter_enabled=settings.embedding_dimensions_parameter_enabled,
        dataset_path=backend_root / "evaluation" / "knowledge_retrieval_dataset.jsonl",
        fixture_path=backend_root / "evaluation" / "knowledge_retrieval_fixture.jsonl",
        baseline_path=backend_root / "evaluation" / "knowledge_retrieval_real_baseline.json",
        top_k=3,
        min_score=0.0,
    )


def resolve_api_key(api_key_env: str | None) -> str | None:
    return os.getenv(api_key_env) if api_key_env else None
