"""Retrieval Evaluation baseline 模块。

职责：生成、比较并持久化检索质量 baseline，冻结 Provider 与数据集身份及关键质量指标。
边界：只负责离线质量门禁数据，不执行检索、不提供第二套 Provider。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

QUALITY_METRICS = ("recall_at_k", "precision_at_k", "mrr")
IDENTITY_FIELDS = (
    "provider",
    "model",
    "embedding_dimension",
    "dataset_version",
    "dataset_sha256",
    "retrieval_mode",
    "top_k",
    "model_profile_id",
    "provider_id",
)


def _identity(metadata: dict[str, Any]) -> dict[str, Any]:
    # 评估 baseline 的身份字段允许历史 baseline 缺省；一旦选定治理模型档案，
    # 模型档案与 Provider ID 就必须成为冻结 baseline 身份的一部分。
    return {
        field: metadata[field]
        for field in IDENTITY_FIELDS
        if field in metadata and metadata[field] is not None
    }


def build_baseline(metadata: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    return _identity(metadata) | {
        "metrics": {
            metric: float(metrics[metric])
            for metric in QUALITY_METRICS
        },
    }


def build_regression_report(
    metadata: dict[str, Any],
    metrics: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    current_identity = _identity(metadata)
    identity_changes = {
        field: {
            "baseline": baseline.get(field),
            "current": current_identity.get(field),
        }
        for field in IDENTITY_FIELDS
        if field in current_identity and baseline.get(field) != current_identity[field]
    }
    baseline_metrics = baseline.get("metrics", {})
    current_metrics = {
        metric: float(metrics[metric])
        for metric in QUALITY_METRICS
    }
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
        "baseline_metrics": {
            metric: float(baseline_metrics.get(metric, 0.0))
            for metric in QUALITY_METRICS
        },
        "current_metrics": current_metrics,
        "metric_deltas": metric_deltas,
        "quality_regressions": regressions,
        "provider_error_rate": float(metrics["error_rate"]),
    }


def compare_baseline(
    metadata: dict[str, Any],
    metrics: dict[str, Any],
    baseline: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    current_identity = _identity(metadata)
    for field, actual in current_identity.items():
        expected = baseline.get(field)
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
    path.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
