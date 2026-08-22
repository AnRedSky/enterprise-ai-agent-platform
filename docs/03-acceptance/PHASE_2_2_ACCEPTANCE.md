# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**进行中 / 2.2-B、2.2-C 与当前 2.2-D regression scope 已由开发者此前本地实际验证；最新 main 的 Scheduled Trigger Real API 与 Real Provider runner 暴露新的回归问题，本轮已修复但尚未重新验证。**
> 未执行的 Gate 不得标记 Passed。

## 1. Acceptance Scope

验证现有 Knowledge / RAG / Retrieval 链路是否能够通过真实 Embedding Provider、固定评测数据集和可重复指标形成生产质量闭环。

## 2. Acceptance Gates

### A. Product / Retrieval Quality Contract — **已形成**

- [x] 真实 Embedding Provider Contract 边界冻结。
- [x] Evaluation Dataset / Corpus 边界冻结。
- [x] Dataset version / case schema 口径冻结。
- [x] Recall@K 定义冻结。
- [x] Precision@K 定义冻结。
- [x] MRR 定义冻结。
- [x] Citation correctness 定义冻结。
- [x] latency / provider error rate 观察口径冻结。
- [x] baseline 与 regression comparison 规则冻结。
- [x] failure / fallback semantics 冻结。

### B. Evaluation Dataset / Runner — **待重新验证**

- [x] Dataset Loader 对当前 JSONL 执行结构、ID、query、relevant chunk 校验。
- [x] Dataset 支持 `expected_citation_targets`，并要求其属于 `relevant_chunk_ids`。
- [x] Evaluation runner 可重复执行设计与实现完成。
- [x] 结果包含 dataset schema version、retrieval mode、case detail、latency、error 与聚合指标。
- [x] Recall@K / Precision@K / MRR / error rate / latency 自动化计算接入现有 evaluation service。
- [x] Citation correctness Contract 与单元测试已实现；观察结果现在可显式携带真实 runtime citation targets。
- [x] 失败 case 可通过 case detail 定位。
- [ ] 最新 main fixture hydration 修复后的真实 runner 尚未由开发者本地重新执行。

### C. Real Provider Quality Gate — **待重新验证**

- [x] 使用真实 Embedding Provider 的 runner 已实现并实际执行。
- [x] 使用真实 PostgreSQL / pgvector Retrieval 链路。
- [x] Provider failure 保留为 observation / error，不静默 fallback。
- [x] 显式 fallback 字段进入结果；此前 Gate 实际 `fallback_used=false`、`fallback_count=0`。
- [x] Mock 结果不作为真实质量证据。
- [x] Provider / model / dimension / dataset / retrieval mode / top-k identity 纳入 baseline。
- [x] 首次真实运行使用 `--freeze-baseline` 冻结真实 baseline。
- [x] 使用冻结 baseline 重跑并确认 regression Gate（此前验证；本轮修复后需重新执行）。
- [ ] 最新 main fixture hydration 修复后的 Real Provider Gate 尚未重新执行。

既有冻结 baseline：

```text
provider=ollama
model=nomic-embed-text:latest
embedding_dimension=768
cases=5
recall@3=0.6
precision@3=0.333333
mrr=0.6
```

### D. Regression / Traceability — **部分完成**

- [x] Provider / model / dataset identity 可进入 baseline 对比。
- [x] Dimension / retrieval mode / top-k identity 可进入 baseline 对比。
- [x] Recall@K / Precision@K / MRR metric delta 可输出 regression report。
- [x] Provider error rate 纳入 regression report。
- [x] Citation correctness Contract、expected citation targets 与错误场景单元测试已实现。
- [x] `RetrievalEvaluationObservation` 可显式记录 runtime `cited_chunk_ids`，聚合器据此计算 citation correctness。
- [x] Real-provider runner 通过 `VectorKnowledgeRetrievalService` 取得真实 citation/source metadata。
- [x] 评测结果带 `evaluation_run_id`、provider/model/dimension/dataset/retrieval mode/top-k/citation source identity。
- [ ] 评测结果持久化接入现有 Retrieval Debug / Audit / Observability 查询模型。

## 3. 最新 main 失败证据与修复

### Scheduled Trigger Real API

开发者最新反馈为 28 passed / 2 failed：

- execution row 已创建，但测试在 `pending` 中间态立即断言 `completed`；
- 双 worker test 默认使用 `recovery_slots=2`，把 current 与 recovery dispatch 一起计数。

修复后测试 helper 等待 terminal state，双 worker test 使用 `recovery_slots=1` 仅验证同一 slot。

### Real Provider Retrieval

开发者最新反馈为 5/5 provider calls 成功，但正式 Runtime Retrieval hydration 后 `retrieved_chunk_ids=[]`，Recall@3=0、MRR=0、provider error rate=0。根因为 evaluation fixture 写入的 document-version 状态与 Runtime Retrieval 的 `ready` contract 不一致。

修复后 fixture 使用 `status='ready'`、`ingestion_status='ready'`，vector index 在写入 pgvector 后由 runner 设置为 `ready`。本轮尚未由开发者重新执行验证。

## 4. 2.2-D 当前结论

真实 Runtime citation evidence bridge 已完成，但完整 Traceability Gate 仍未完成。下一独立开发任务是把 evaluation run / case / regression result 持久化到现有 Retrieval Debug / Audit / Observability 查询模型；必须在本轮 Gate 恢复后继续。

## 5. 本轮修复后的本地验证流程

```powershell
cd backend
uv run pytest -q tests/unit/test_vector_knowledge_retrieval.py tests/unit/test_retrieval_evaluation.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
uv run python .\scripts\evaluation\knowledge\run_knowledge_retrieval_real_provider.py --k 3
```

如 baseline 已存在，runner 必须保持 `baseline.status=checked`；不得因为本次修复而执行 `--freeze-baseline`。只有明确发生合法 Provider/model/dataset/retrieval identity 变化时才重新冻结 baseline。
