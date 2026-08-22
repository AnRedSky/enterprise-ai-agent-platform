from pathlib import Path
from types import SimpleNamespace

from app.services.retrieval_evaluation_config import RetrievalEvaluationConfig, config_from_settings, validate_config


def base_config(**overrides):
    values = {
        "embedding_provider": "ollama",
        "embedding_provider_name": "local-ollama",
        "embedding_base_url": "http://localhost:11434",
        "embedding_api_key": None,
        "embedding_model": "nomic-embed-text:latest",
        "embedding_timeout_seconds": 30.0,
        "embedding_dimension": 768,
        "embedding_dimensions_parameter_enabled": False,
        "dataset_path": Path("dataset.jsonl"),
        "fixture_path": Path("fixture.jsonl"),
        "baseline_path": Path("baseline.json"),
        "top_k": 3,
        "min_score": 0.0,
    }
    values.update(overrides)
    return RetrievalEvaluationConfig(**values)


def test_evaluation_config_accepts_custom_provider_and_quality_parameters():
    config = base_config(
        embedding_provider="openai-compatible",
        embedding_provider_name="company-openai-gateway",
        embedding_base_url="http://localhost:8080/v1",
        embedding_api_key="secret",
        embedding_model="custom-embedding",
        embedding_dimension=1024,
        embedding_dimensions_parameter_enabled=True,
        top_k=7,
        min_score=0.25,
        min_recall_at_k=0.8,
        min_precision_at_k=0.5,
        min_mrr=0.7,
        min_citation_correctness=0.9,
        max_error_rate=0.05,
    )
    validate_config(config)


def test_evaluation_config_uses_application_defaults():
    settings = SimpleNamespace(
        embedding_provider="ollama",
        embedding_provider_name="team-ollama",
        embedding_base_url="http://embedding.local",
        embedding_api_key=None,
        embedding_model="custom-embed-v2",
        embedding_timeout_seconds=17.0,
        embedding_dimension=1024,
        embedding_dimensions_parameter_enabled=True,
        retrieval_evaluation_top_k=8,
        retrieval_evaluation_min_score=0.31,
        retrieval_evaluation_min_recall_at_k=0.75,
        retrieval_evaluation_min_precision_at_k=0.5,
        retrieval_evaluation_min_mrr=0.6,
        retrieval_evaluation_min_citation_correctness=0.8,
        retrieval_evaluation_max_error_rate=0.02,
    )
    config = config_from_settings(backend_root=Path("backend"), settings=settings)
    assert config.embedding_provider_name == "team-ollama"
    assert config.embedding_model == "custom-embed-v2"
    assert config.embedding_dimension == 1024
    assert config.top_k == 8
    assert config.min_score == 0.31
    assert config.min_recall_at_k == 0.75
    assert config.min_precision_at_k == 0.5
    assert config.min_mrr == 0.6
    assert config.min_citation_correctness == 0.8
    assert config.max_error_rate == 0.02


def test_evaluation_config_rejects_invalid_quality_threshold():
    try:
        validate_config(base_config(min_recall_at_k=1.1))
    except ValueError as exc:
        assert "min_recall_at_k" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_evaluation_config_requires_api_key_for_openai_compatible():
    try:
        validate_config(base_config(embedding_provider="openai-compatible"))
    except ValueError as exc:
        assert "embedding_api_key" in str(exc)
    else:
        raise AssertionError("expected ValueError")
