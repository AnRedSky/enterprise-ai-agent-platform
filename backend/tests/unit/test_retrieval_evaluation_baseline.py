from pathlib import Path

from app.services.retrieval_evaluation_baseline import (
    build_baseline,
    compare_baseline,
    write_baseline,
)


def metadata(**overrides):
    return {
        "provider": "openai-compatible",
        "model": "text-embedding-test",
        "embedding_dimension": 1536,
        "dataset_version": "1",
        "dataset_sha256": "abc123",
        "retrieval_mode": "real-provider-pgvector",
        "top_k": 3,
        **overrides,
    }


def test_build_baseline_records_provider_identity_and_quality_metrics():
    metrics = {"recall_at_k": 1.0, "precision_at_k": 0.4, "mrr": 0.9}

    assert build_baseline(metadata(), metrics) == {
        **metadata(),
        "metrics": metrics,
    }


def test_compare_baseline_rejects_identity_change_and_quality_regression():
    actual_metadata = metadata(model="new-model")
    metrics = {
        "recall_at_k": 0.8,
        "precision_at_k": 0.4,
        "mrr": 0.7,
        "error_rate": 0.0,
    }
    baseline = {
        **metadata(model="old-model"),
        "metrics": {"recall_at_k": 1.0, "precision_at_k": 0.5, "mrr": 0.9},
    }

    failures = compare_baseline(actual_metadata, metrics, baseline)

    assert "model changed: 'new-model' != baseline 'old-model'" in failures
    assert "recall_at_k regressed: 0.8 < baseline 1.0" in failures
    assert "mrr regressed: 0.7 < baseline 0.9" in failures


def test_compare_baseline_rejects_dataset_content_change():
    failures = compare_baseline(
        metadata(dataset_sha256="new-hash"),
        {"recall_at_k": 1.0, "precision_at_k": 0.4, "mrr": 1.0, "error_rate": 0.0},
        {**metadata(dataset_sha256="old-hash"), "metrics": {"recall_at_k": 1.0, "precision_at_k": 0.4, "mrr": 1.0}},
    )

    assert "dataset_sha256 changed: 'new-hash' != baseline 'old-hash'" in failures


def test_compare_baseline_rejects_provider_errors():
    baseline = {
        **metadata(),
        "metrics": {"recall_at_k": 1.0, "precision_at_k": 0.4, "mrr": 1.0},
    }
    metrics = {
        "recall_at_k": 1.0,
        "precision_at_k": 0.4,
        "mrr": 1.0,
        "error_rate": 0.2,
    }

    assert compare_baseline(metadata(), metrics, baseline) == [
        "provider error rate is non-zero: 0.2"
    ]


def test_write_baseline_is_versioned_json(tmp_path: Path):
    path = tmp_path / "baseline.json"
    write_baseline(
        path,
        {
            **metadata(),
            "metrics": {"recall_at_k": 1.0, "precision_at_k": 0.5, "mrr": 1.0},
        },
    )

    assert path.exists()
    assert '"provider": "openai-compatible"' in path.read_text(encoding="utf-8")
