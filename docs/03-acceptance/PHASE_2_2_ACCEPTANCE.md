# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**进行中 / 2.2-B、2.2-C、2.2-D 当前定义范围已由开发者本轮本地重新验证通过。**
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
- [x] 当前 main 的真实 runner 已由开发者本轮实际重新执行并通过。

### C. Real Provider Quality Gate — **已验证**

- [x] 使用真实 Embedding Provider 的 runner 已实现并实际执行。
- [x] 使用真实 PostgreSQL / pgvector Retrieval 链路。
- [x] Provider failure 保留为 observation / error，不静默 fallback。
- [x] 显式 fallback 字段进入结果；本轮实际 `fallback_used=false`、`fallback_count=0`。
- [x] Mock 结果不作为真实质量证据。
- [x] Provider / model / dimension / dataset / retrieval mode / top-k identity 纳入 baseline。
- [x] 使用冻结 baseline 重跑并确认 regression Gate。

当前冻结 baseline：

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

### D. Regression / Traceability — **已验证当前定义范围**

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
- [x] 新增 Runtime Trace API contract 测试，覆盖 route registration 与 bearer authentication。
- [x] 新增 Real API traceability 测试，覆盖真实 runner → execution/case/summary → audit 查询链路。
- [x] 本轮完整 Real API gate 已实际执行并通过 31 个测试。

## 3. 本轮实际 Gate 结果

```text
API Runtime Contract: 2 passed
Real HTTP API: 31 passed
Backend regression: 309 passed, 31 deselected
Migration head: 0024_embedding_dimension_contract
Backend Release / Regression Gate: passed
```

## 4. 当前 Acceptance 结论

2.2-D 当前定义的 traceability persistence / API contract / Real API 覆盖已具备实际通过证据。此前的 baseline 缺失阻塞已通过仓库固化冻结 baseline 修复，并在本轮完整 Real API 与 Backend Release / Regression Gate 中得到验证。

但当前真实 Provider 指标仍为 Recall@3=0.6、Precision@3=0.333333、Citation correctness=0.333333。它们是冻结 baseline 的实际质量表现，而不是“语义质量已经达到最终产品目标”的证明。因此 Phase 2.2 是否关闭，需要产品侧明确质量目标后再做结论；不得通过修改 baseline 掩盖当前指标。

## 5. 本轮完整自动化测试流程

```powershell
cd backend

# 1. API Contract
uv run pytest -q tests/api_contract/test_api_runtime_endpoints.py

# 2. 完整 Real HTTP API Gate（包含 Retrieval traceability）
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1

# 3. Real Provider Quality Gate；已有 baseline 时禁止 --freeze-baseline
uv run python .\scripts\evaluation\knowledge\run_knowledge_retrieval_real_provider.py --k 3

# 4. 完整 Backend Release / Regression Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

自动化验收要求：真实 runner 返回 0 且 `quality_gate=passed`；Real API gate 全部通过；Backend regression / migration / Real API 三层 Gate 全部通过。Trace API 的 `evaluation_run_id` 必须能够查询到 execution、case、summary 与对应 Audit Log。

## 6. 下一步

1. 先形成当前 Recall@3 / Precision@3 / Citation correctness 是否满足产品目标的明确结论。
2. 若不满足，先形成质量提升方案与架构决策，再实施检索质量优化；不得通过降低 gate 或修改 baseline 解决。
3. 若满足，则完成 Phase 2.2 关闭文档与最终 Acceptance 记录；在正式立项前不得创建新的 Phase。
