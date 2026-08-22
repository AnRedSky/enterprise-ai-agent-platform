from app.services.retrieval_evaluation_config import RetrievalEvaluationConfig, validate_config


def base_config(**overrides):
    values = {
        "embedding_provider": "ollama",
        "embedding_base_url": "http://localhost:11434",
        "embedding_api_key": None,
        "embedding_model": "nomic-embed-text:latest",
        "embedding_timeout_seconds": 30.0,
        "embedding_dimension": 768,
        "dataset_path": __import__("pathlib").Path("dataset.jsonl"),
        "fixture_path": __import__("pathlib").Path("fixture.jsonl"),
        "baseline_path": __import__("pathlib").Path("baseline.json"),
        "top_k": 3,
        "min_score": 0.0,
    }
    values.update(overrides)
    return RetrievalEvaluationConfig(**values)


def test_evaluation_config_accepts_custom_provider_and_quality_parameters():
    config = base_config(
        embedding_provider="openai-compatible",
        embedding_base_url="http://localhost:8080/v1",
        embedding_api_key="secret",
        embedding_model="custom-embedding",
        embedding_dimension=1024,
        top_k=7,
        min_score=0.25,
        min_recall_at_k=0.8,
        min_precision_at_k=0.5,
        min_mrr=0.7,
        min_citation_correctness=0.9,
        max_error_rate=0.05,
    )
    validate_config(config)


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
