# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**进行中 / 2.2-B、2.2-C 已由开发者本地重新验证通过；2.2-D 的 Runtime evidence bridge 已完成，本轮开始接入持久化 Traceability。**
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

### B. Evaluation Dataset / Runner — **已验证**

- [x] Dataset Loader 对当前 JSONL 执行结构、ID、query、relevant chunk 校验。
- [x] Dataset 支持 `expected_citation_targets`，并要求其属于 `relevant_chunk_ids`。
- [x] Evaluation runner 可重复执行设计与实现完成。
- [x] 结果包含 dataset schema version、retrieval mode、case detail、latency、error 与聚合指标。
- [x] Recall@K / Precision@K / MRR / error rate / latency 自动化计算接入现有 evaluation service。
- [x] Citation correctness Contract 与单元测试已实现；观察结果现在可显式携带真实 runtime citation targets。
- [x] 失败 case 可通过 case detail 定位。
- [x] 最新 main fixture hydration 修复后的真实 runner 已由开发者本地重新执行。

### C. Real Provider Quality Gate — **已验证**

- [x] 使用真实 Embedding Provider 的 runner 已实现并实际执行。
- [x] 使用真实 PostgreSQL / pgvector Retrieval 链路。
- [x] Provider failure 保留为 observation / error，不静默 fallback。
- [x] 显式 fallback 字段进入结果；本轮实际 `fallback_used=false`、`fallback_count=0`。
- [x] Mock 结果不作为真实质量证据。
- [x] Provider / model / dimension / dataset / retrieval mode / top-k identity 纳入 baseline。
- [x] 首次真实运行使用 `--freeze-baseline` 冻结真实 baseline。
- [x] 使用冻结 baseline 重跑并确认 regression Gate。

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

本轮实际 Real Provider 结果：

```text
recall@3=0.6
precision@3=0.333333
mrr=0.6
citation_correctness=0.333333
provider_error_rate=0
quality_gate=passed
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
- [x] Evaluation run / case / regression summary 已持久化到现有 `executions` / `execution_events` Observability 模型。
- [x] Evaluation completion 已写入现有 `audit_logs`。
- [x] 新增 admin-only Retrieval Evaluation Trace 查询入口，复用 Runtime Observability timeline。
- [ ] Trace persistence / API contract 尚未由开发者本地重新执行验证。

## 3. 已解决的最新 main 问题

### Scheduled Trigger Real API

开发者本地最终验证为：

```text
Real HTTP API: 30 passed
```

修复了 execution terminal-state 等待竞态，并将双 worker test 限制到同一个 slot。

### Real Provider Retrieval

开发者本地最终验证为：

```text
cases=5
provider_error_rate=0
recall@3=0.6
precision@3=0.333333
mrr=0.6
citation_correctness=0.333333
quality_gate=passed
```

说明 Runtime Retrieval hydration contract 已恢复，且没有修改冻结 baseline。

## 4. 2.2-D 当前结论

真实 Runtime citation evidence bridge 与 Real Provider Quality Gate 已完成。当前独立任务是验证新增 evaluation trace persistence：runner 生成的 `evaluation_run_id` 必须能从数据库 / Runtime Observability 查询到 run、case、summary，并在 Audit Log 中存在对应记录。

## 5. 本轮 Traceability Persistence 本地验证流程

```powershell
cd backend

# 1. 单元 / 回归
uv run pytest -q tests/unit/test_vector_knowledge_retrieval.py tests/unit/test_retrieval_evaluation.py
uv run pytest -q

# 2. migration + Real HTTP API
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1

# 3. Real Provider Quality Gate；已有 baseline 时禁止 --freeze-baseline
uv run python .\scripts\evaluation\knowledge\run_knowledge_retrieval_real_provider.py --k 3

# 4. 从 runner 输出中取得 evaluation_run_id，然后使用管理员 Token 查询
# GET /api/v1/runtime/retrieval-evaluations/{evaluation_run_id}
```

验收要求：查询结果应包含一个 `ExecutionTimelineResponse`，其中 execution 的 `trace_id` 等于 `evaluation_run_id`，events 至少包含 `retrieval_evaluation_case` 与 `retrieval_evaluation_summary`；Audit Log 应存在 `action=retrieval_evaluation.completed` 的记录。
