from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.evaluate_knowledge_retrieval_baseline import evaluate

BASELINE = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_baseline.json"
METRICS = ("recall_at_k", "precision_at_k", "mrr")


def load_baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def compare_quality(current: dict, baseline: dict) -> list[str]:
    violations: list[str] = []

    if current.get("mode") != baseline.get("mode"):
        violations.append(
            f"mode changed: baseline={baseline.get('mode')!r}, current={current.get('mode')!r}"
        )

    if current.get("case_count") != baseline.get("case_count"):
        violations.append(
            f"case_count changed: baseline={baseline.get('case_count')}, current={current.get('case_count')}"
        )

    for metric in METRICS:
        baseline_value = float(baseline[metric])
        current_value = float(current[metric])
        if current_value < baseline_value:
            violations.append(
                f"{metric} regressed: baseline={baseline_value:.6f}, current={current_value:.6f}"
            )

    baseline_cases = {case["query"]: case for case in baseline.get("cases", [])}
    current_cases = {case["query"]: case for case in current.get("cases", [])}
    if set(current_cases) != set(baseline_cases):
        violations.append("evaluation case queries changed")
    else:
        for query, baseline_case in baseline_cases.items():
            current_case = current_cases[query]
            for metric in METRICS:
                baseline_value = float(baseline_case["metrics"][metric])
                current_value = float(current_case["metrics"][metric])
                if current_value < baseline_value:
                    violations.append(
                        f"case {query!r} {metric} regressed: "
                        f"baseline={baseline_value:.6f}, current={current_value:.6f}"
                    )

    return violations


def main() -> int:
    baseline = load_baseline()
    current = evaluate()
    violations = compare_quality(current, baseline)
    payload = {
        "mode": current.get("mode"),
        "case_count": current.get("case_count"),
        "metrics": {metric: current.get(metric) for metric in METRICS},
        "baseline_metrics": {metric: baseline.get(metric) for metric in METRICS},
        "passed": not violations,
        "violations": violations,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
