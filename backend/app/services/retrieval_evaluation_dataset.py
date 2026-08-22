from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.retrieval_evaluation import RetrievalEvaluationCase


DATASET_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class RetrievalEvaluationDataset:
    """Validated evaluation dataset loaded from JSONL.

    The dataset is evaluation input only. Production retrieval must continue
    to read knowledge data from PostgreSQL/pgvector; this loader never serves
    retrieval results itself.
    """

    source: Path
    cases: tuple[RetrievalEvaluationCase, ...]
    schema_version: str = DATASET_SCHEMA_VERSION


def _validate_case(row: dict[str, Any], line_number: int) -> RetrievalEvaluationCase:
    if not isinstance(row, dict):
        raise ValueError(f"dataset line {line_number} must be a JSON object")

    case_id = row.get("id")
    query = row.get("query")
    relevant = row.get("relevant_chunk_ids")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError(f"dataset line {line_number} requires a non-empty string id")
    if not isinstance(query, str) or not query.strip():
        raise ValueError(f"dataset case {case_id!r} requires a non-empty string query")
    if not isinstance(relevant, list) or not relevant or not all(isinstance(item, str) and item.strip() for item in relevant):
        raise ValueError(f"dataset case {case_id!r} requires a non-empty relevant_chunk_ids list")

    return RetrievalEvaluationCase(query=query, relevant_chunk_ids=frozenset(relevant))


def load_retrieval_evaluation_dataset(path: Path) -> RetrievalEvaluationDataset:
    if not path.exists():
        raise FileNotFoundError(f"retrieval evaluation dataset not found: {path}")

    cases: list[RetrievalEvaluationCase] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in dataset line {line_number}: {exc.msg}") from exc
        case = _validate_case(row, line_number)
        case_id = row["id"]
        if case_id in seen_ids:
            raise ValueError(f"duplicate dataset case id: {case_id}")
        seen_ids.add(case_id)
        cases.append(case)

    if not cases:
        raise ValueError(f"retrieval evaluation dataset is empty: {path}")

    return RetrievalEvaluationDataset(source=path, cases=tuple(cases))
