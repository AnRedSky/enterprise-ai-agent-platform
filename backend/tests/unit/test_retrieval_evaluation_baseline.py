from pathlib import Path

from app.services.retrieval_evaluation import (
    build_baseline,
    build_regression_report,
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


def test_build_baseline_records_governed_profile_identity_when_selected():
    baseline = build_baseline(
        metadata(
            model_profile_id="profile-1",
            provider_id="provider-1",
            provider_name="custom-ollama",
            provider_type="ollama",
        ),
        {"recall_at_k": 1.0, "precision_at_k": 0.4, "mrr": 0.9},
    )

    assert baseline["model_profile_id"] == "profile-1"
    assert baseline["provider_id"] == "provider-1"


def test_build_regression_report_exposes_identity_changes_and_metric_deltas():
    report = build_regression_report(
        metadata(model="new-model"),
        {
            "recall_at_k": 0.8,
            "precision_at_k": 0.5,
            "mrr": 1.0,
            "error_rate": 0.0,
        },
        {
            **metadata(model="old-model"),
            "metrics": {"recall_at_k": 1.0, "precision_at_k": 0.4, "mrr": 0.9},
        },
    )

    assert report["identity_changed"] is True
    assert report["identity_changes"]["model"] == {
        "baseline": "old-model",
        "current": "new-model",
    }
    assert report["metric_deltas"] == {
        "recall_at_k": -0.19999999999999996,
        "precision_at_k": 0.09999999999999998,
        "mrr": 0.09999999999999998,
    }
    assert report["quality_regressions"] == {"recall_at_k": -0.19999999999999996}
    assert report["provider_error_rate"] == 0.0


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


def test_compare_baseline_rejects_governed_profile_identity_change():
    actual = metadata(model_profile_id="profile-new", provider_id="provider-1")
    baseline = {
        **metadata(model_profile_id="profile-old", provider_id="provider-1"),
        "metrics": {"recall_at_k": 1.0, "precision_at_k": 0.4, "mrr": 1.0},
    }

    failures = compare_baseline(
        actual,
        {"recall_at_k": 1.0, "precision_at_k": 0.4, "mrr": 1.0, "error_rate": 0.0},
        baseline,
    )

    assert "model_profile_id changed: 'profile-new' != baseline 'profile-old'" in failures


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
