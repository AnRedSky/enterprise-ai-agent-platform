"""Retrieval Evaluation 数据集加载测试。

职责：验证离线检索评估数据集的 JSONL 校验、引用目标和 Case 指标行为。
边界：仅验证评估输入，不触碰生产检索数据与 Provider。
"""

from pathlib import Path

import pytest

from app.services.retrieval_evaluation import RetrievalEvaluationCase, citation_correctness, evaluate_case
from app.services.retrieval_evaluation.dataset import (
    DATASET_SCHEMA_VERSION,
    load_retrieval_evaluation_dataset,
)


DATASET = Path(__file__).parents[2] / "evaluation" / "knowledge_retrieval_dataset.jsonl"


def test_load_current_dataset_returns_validated_cases():
    dataset = load_retrieval_evaluation_dataset(DATASET)

    assert dataset.schema_version == DATASET_SCHEMA_VERSION
    assert len(dataset.cases) == 5
    assert dataset.cases[0].query == "FastAPI Agent Runtime"
    assert dataset.cases[0].expected_citation_targets == frozenset({"chunk-fastapi-runtime"})
    assert dataset.cases[3].relevant_chunk_ids == frozenset({"chunk-expense-policy", "chunk-approval-process"})
    assert dataset.cases[3].expected_citation_targets == frozenset({"chunk-expense-policy", "chunk-approval-process"})


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


def test_loader_rejects_citation_target_outside_relevant_chunks(tmp_path):
    path = tmp_path / "dataset.jsonl"
    path.write_text(
        '{"id":"case-1","query":"q","relevant_chunk_ids":["a"],"expected_citation_targets":["b"]}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected_citation_targets must be a subset"):
        load_retrieval_evaluation_dataset(path)


def test_citation_correctness_requires_retrieved_and_expected_target():
    assert citation_correctness(["a"], ["a", "noise"], {"a"}) == 1.0
    assert citation_correctness(["a"], ["noise"], {"a"}) == 0.0
    assert citation_correctness(["noise"], ["noise"], {"a"}) == 0.0
    assert citation_correctness([], ["a"], {"a"}) == 0.0


def test_evaluate_case_includes_citation_correctness():
    case = RetrievalEvaluationCase(
        query="q",
        relevant_chunk_ids=frozenset({"a", "b"}),
        expected_citation_targets=frozenset({"a"}),
    )

    metrics = evaluate_case(case, ["a", "noise"], k=2, cited_targets=["a"])

    assert metrics["citation_correctness"] == 1.0
    assert metrics["precision_at_k"] == 0.5
