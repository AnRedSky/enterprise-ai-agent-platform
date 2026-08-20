from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.knowledge_retrieval import KnowledgeRetrievalService
from app.services.retrieval_evaluation import RetrievalEvaluationCase, aggregate_evaluation, evaluate_case

DATASET = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_dataset.jsonl"
CORPUS = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_corpus.jsonl"
OUTPUT = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_baseline.json"


def load_cases() -> list[RetrievalEvaluationCase]:
    return [
        RetrievalEvaluationCase(item["query"], frozenset(item["relevant_chunk_ids"]))
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for item in [json.loads(line)]
    ]


def load_corpus() -> list[dict[str, str]]:
    return [
        {"chunk_id": item["chunk_id"], "content": item["content"]}
        for line in CORPUS.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for item in [json.loads(line)]
    ]


def rank_case(query: str, corpus: list[dict[str, str]]) -> list[str]:
    scored = [
        (item["chunk_id"], KnowledgeRetrievalService._score(query, item["content"]))
        for item in corpus
    ]
    scored = [item for item in scored if item[1] > 0]
    scored.sort(key=lambda item: (-item[1], item[0]))
    return [chunk_id for chunk_id, _score in scored]


def evaluate() -> dict:
    cases = load_cases()
    corpus = load_corpus()
    rankings = [rank_case(case.query, corpus) for case in cases]
    summary = aggregate_evaluation(cases, rankings, k=3)
    details = [
        {"query": case.query, "ranking": ranking, "metrics": evaluate_case(case, ranking, k=3)}
        for case, ranking in zip(cases, rankings)
    ]
    return {
        "mode": KnowledgeRetrievalService.RETRIEVAL_MODE,
        **summary,
        "case_count": len(cases),
        "cases": details,
    }


def main() -> int:
    payload = evaluate()
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
