"""Retrieval Evaluation 数据集加载测试。

职责：验证离线检索评估数据集的 JSONL 校验与 canonical 数据集加载入口。
边界：仅验证评估输入，不触碰生产检索数据与 Provider。
"""

from pathlib import Path

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
