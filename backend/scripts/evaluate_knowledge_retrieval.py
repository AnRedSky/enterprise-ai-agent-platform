from __future__ import annotations

import json
import sys
from pathlib import Path

from app.services.retrieval_evaluation import RetrievalEvaluationCase, aggregate_evaluation


DATASET = Path(__file__).resolve().parents[1] / "evaluation" / "knowledge_retrieval_dataset.jsonl"


def load_cases() -> list[RetrievalEvaluationCase]:
    cases: list[RetrievalEvaluationCase] = []
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        cases.append(RetrievalEvaluationCase(item["query"], frozenset(item["relevant_chunk_ids"])))
    return cases


def main() -> int:
    cases = load_cases()
    if len(cases) < 5:
        raise SystemExit("retrieval evaluation dataset must contain at least 5 cases")

    # This command validates the dataset and metric pipeline without requiring a
    # database or vector provider. Replace rankings with provider output in the
    # next evaluation stage while keeping the same metric contract.
    rankings = [list(case.relevant_chunk_ids) for case in cases]
    result = aggregate_evaluation(cases, rankings, k=3)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
