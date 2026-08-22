from pathlib import Path

import pytest

from app.services.retrieval_evaluation_dataset import (
    DATASET_SCHEMA_VERSION,
    load_retrieval_evaluation_dataset,
)


DATASET = Path(__file__).parents[2] / "evaluation" / "knowledge_retrieval_dataset.jsonl"


def test_load_current_dataset_returns_validated_cases():
    dataset = load_retrieval_evaluation_dataset(DATASET)

    assert dataset.schema_version == DATASET_SCHEMA_VERSION
    assert len(dataset.cases) == 5
    assert dataset.cases[0].query == "FastAPI Agent Runtime"
    assert dataset.cases[3].relevant_chunk_ids == frozenset({"chunk-expense-policy", "chunk-approval-process"})


def test_loader_rejects_duplicate_case_ids(tmp_path):
    path = tmp_path / "dataset.jsonl"
    path.write_text(
        '{"id":"case-1","query":"q","relevant_chunk_ids":["a"]}\n'
        '{"id":"case-1","query":"q2","relevant_chunk_ids":["b"]}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate dataset case id"):
        load_retrieval_evaluation_dataset(path)


def test_loader_rejects_invalid_case_shape(tmp_path):
    path = tmp_path / "dataset.jsonl"
    path.write_text('{"id":"case-1","query":"","relevant_chunk_ids":[]}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="requires a non-empty string query"):
        load_retrieval_evaluation_dataset(path)


def test_loader_rejects_invalid_json(tmp_path):
    path = tmp_path / "dataset.jsonl"
    path.write_text('{"id":"case-1"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON in dataset line 1"):
        load_retrieval_evaluation_dataset(path)
