from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.retrieval_evaluation import RetrievalEvaluationCase, RetrievalEvaluationObservation, aggregate_observations

DATASET = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_dataset.jsonl"
BASELINE = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_baseline.json"


def load_cases() -> list[RetrievalEvaluationCase]:
    return [
        RetrievalEvaluationCase(item["query"], frozenset(item["relevant_chunk_ids"]))
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for item in [json.loads(line)]
    ]


def load_observations(path: Path) -> tuple[str, list[RetrievalEvaluationObservation]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"evaluation result file is empty: {path}")
    modes = {row.get("mode") for row in rows}
    if len(modes) != 1 or None in modes:
        raise ValueError("all evaluation results must use one non-empty retrieval mode")
    by_query = {row.get("query"): row for row in rows}
    observations: list[RetrievalEvaluationObservation] = []
    for case in load_cases():
        row = by_query.get(case.query)
        if row is None:
            raise ValueError(f"missing evaluation result for query: {case.query}")
        observations.append(
            RetrievalEvaluationObservation(
                retrieved_chunk_ids=tuple(str(item) for item in row.get("ranking", [])),
                latency_ms=float(row.get("latency_ms", 0.0)),
                error=str(row["error"]) if row.get("error") else None,
            )
        )
    return str(next(iter(modes))), observations


def quality_gate(metrics: dict[str, float | int], baseline: dict) -> list[str]:
    failures: list[str] = []
    for metric in ("recall_at_k", "mrr"):
        actual = float(metrics[metric])
        expected = float(baseline.get(metric, 0.0))
        if actual < expected:
            failures.append(f"{metric} regressed: {actual} < baseline {expected}")
    if float(metrics["error_rate"]) > 0:
        failures.append(f"provider error rate is non-zero: {metrics['error_rate']}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate live Knowledge Retrieval provider output")
    parser.add_argument("results", type=Path, help="JSONL result file from a live/manual retrieval run")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    if args.k < 1:
        raise SystemExit("--k must be greater than zero")

    cases = load_cases()
    if len(cases) < 5:
        raise SystemExit("retrieval evaluation dataset must contain at least 5 cases")
    mode, observations = load_observations(args.results)
    metrics = aggregate_observations(cases, observations, k=args.k)
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    failures = quality_gate(metrics, baseline)
    report = {
        "mode": mode,
        "k": args.k,
        **metrics,
        "quality_gate": "failed" if failures else "passed",
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
