# Phase 1.4-E Retrieval Evaluation Baseline

> 本文记录真实 `lexical-v2` 离线评测的执行入口与基线数据。所有开发直接提交 `main`。

## 当前实现

- Evaluation Dataset：`backend/evaluation/knowledge_retrieval_dataset.jsonl`
- Evaluation Corpus：`backend/evaluation/knowledge_retrieval_corpus.jsonl`
- Evaluation runner：`backend/scripts/evaluate_knowledge_retrieval_baseline.py`
- Metric contract：`backend/app/services/retrieval_evaluation.py`
- Retrieval implementation：`backend/app/services/knowledge_retrieval.py`
- Regression test：`backend/tests/test_retrieval_evaluation_runner.py`

Runner 不再使用“把 relevant chunk 直接作为 ranking”的理想化数据，而是读取 corpus，复用生产 `KnowledgeRetrievalService._score()` 的 lexical-v2 scoring，再执行 Recall@K / Precision@K / MRR。

## 本地执行

```powershell
cd backend
uv sync
uv run python .\scripts\evaluate_knowledge_retrieval_baseline.py
uv run pytest -q .\tests\test_retrieval_evaluation_runner.py
```

Runner 会生成本地 `backend/evaluation/knowledge_retrieval_baseline.json`。该文件属于评测产物，不作为业务源码依赖。

## 验收要求

1. ranking 必须来自真实 lexical-v2 scoring。
2. Evaluation Dataset 只定义 query 与 relevant chunk，不参与 ranking。
3. ranking 必须保持 deterministic：score 降序 + chunk_id 升序。
4. 评测输出必须包含整体 Recall@3 / Precision@3 / MRR 与逐 Case ranking。
5. 后续 Embedding / Vector DB provider 必须复用同一 Evaluation Dataset 与 Metric Contract，才能进行可比性评测。

## 下一步

Phase 1.4-E 下一阶段进入 provider adapter 验证：先定义 Embedding Provider 的最小可替换实现，再使用同一 Dataset 对 lexical-v2 与 embedding/vector provider 做 Recall@K / Precision@K / MRR 对比，不直接绑定 Milvus / Elasticsearch 等具体基础设施。
