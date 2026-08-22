from __future__ import annotations

import json
from pathlib import Path
from typing import Any

QUALITY_METRICS = ("recall_at_k", "precision_at_k", "mrr")
IDENTITY_FIELDS = (
    "provider",
    "provider_name",
    "model",
    "embedding_dimension",
    "dataset_version",
    "dataset_sha256",
    "retrieval_mode",
    "top_k",
)


def build_baseline(metadata: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    return {field: metadata[field] for field in IDENTITY_FIELDS} | {
        "metrics": {metric: float(metrics[metric]) for metric in QUALITY_METRICS},
    }


def build_regression_report(metadata: dict[str, Any], metrics: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    identity_changes = {
        field: {"baseline": baseline.get(field), "current": metadata.get(field)}
        for field in IDENTITY_FIELDS
        if baseline.get(field) != metadata.get(field)
    }
    baseline_metrics = baseline.get("metrics", {})
    current_metrics = {metric: float(metrics[metric]) for metric in QUALITY_METRICS}
    metric_deltas = {
        metric: current_metrics[metric] - float(baseline_metrics.get(metric, 0.0))
        for metric in QUALITY_METRICS
    }
    regressions = {
        metric: metric_deltas[metric]
        for metric in ("recall_at_k", "mrr")
        if metric_deltas[metric] < 0
    }
    return {
        "identity_changed": bool(identity_changes),
        "identity_changes": identity_changes,
        "baseline_metrics": {metric: float(baseline_metrics.get(metric, 0.0)) for metric in QUALITY_METRICS},
        "current_metrics": current_metrics,
        "metric_deltas": metric_deltas,
        "quality_regressions": regressions,
        "provider_error_rate": float(metrics["error_rate"]),
    }


def compare_baseline(metadata: dict[str, Any], metrics: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for field in IDENTITY_FIELDS:
        expected = baseline.get(field)
        actual = metadata.get(field)
        if expected != actual:
            failures.append(f"{field} changed: {actual!r} != baseline {expected!r}")

    baseline_metrics = baseline.get("metrics", {})
    for metric in ("recall_at_k", "mrr"):
        actual = float(metrics[metric])
        expected = float(baseline_metrics.get(metric, 0.0))
        if actual < expected:
            failures.append(f"{metric} regressed: {actual} < baseline {expected}")

    if float(metrics["error_rate"]) > 0:
        failures.append(f"provider error rate is non-zero: {metrics['error_rate']}")
    return failures


def write_baseline(path: Path, baseline: dict[str, Any]) -> None:
    path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
