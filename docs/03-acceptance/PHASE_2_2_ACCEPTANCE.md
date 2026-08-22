# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**进行中 / 2.2-B、2.2-C、2.2-D 当前定义范围已由开发者此前本地重新验证通过；本轮增加 Evaluation Configuration，待开发者本地重新执行相关 Gate 后再记录本轮通过证据。**
> 未执行的 Gate 不得标记 Passed。

## 1. Acceptance Scope

验证现有 Knowledge / RAG / Retrieval 链路是否能够通过真实 Embedding Provider、可配置评测数据集与评估参数、可重复指标形成生产质量闭环。

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

### B. Evaluation Dataset / Runner — **已验证既有范围；配置化增强待本轮执行**

- [x] Dataset Loader 对当前 JSONL 执行结构、ID、query、relevant chunk 校验。
- [x] Dataset 支持 `expected_citation_targets`，并要求其属于 `relevant_chunk_ids`。
- [x] Evaluation runner 可重复执行设计与实现完成。
- [x] 结果包含 dataset schema version、retrieval mode、case detail、latency、error 与聚合指标。
- [x] Recall@K / Precision@K / MRR / error rate / latency 自动化计算接入现有 evaluation service。
- [x] Citation correctness Contract 与单元测试已实现；观察结果现在可显式携带真实 runtime citation targets。
- [x] 失败 case 可通过 case detail 定位。
- [x] 既有 main 的真实 runner 已由开发者实际执行并通过。
- [x] Evaluation model/provider、dataset/fixture/baseline path、top-k、min-score、quality thresholds 已提供显式配置入口。
- [ ] 上述配置化入口的本轮本地 Gate 尚未执行，不提前标记 Passed。

### C. Real Provider Quality Gate — **已验证既有范围**

- [x] 使用真实 Embedding Provider 的 runner 已实现并实际执行。
- [x] 使用真实 PostgreSQL / pgvector Retrieval 链路。
- [x] Provider failure 保留为 observation / error，不静默 fallback。
- [x] 显式 fallback 字段进入结果；既有实际 `fallback_used=false`、`fallback_count=0`。
- [x] Mock 结果不作为真实质量证据。
- [x] Provider / model / dimension / dataset / retrieval mode / top-k identity 纳入 baseline。
- [x] 使用冻结 baseline 重跑并确认 regression Gate。

### D. Regression / Traceability — **已验证既有范围**

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
- [x] 既有完整 Real API gate 已实际执行并通过 31 个测试。
- [x] 本次配置参数进入 evaluation trace metadata；本轮本地持久化验证待执行。

## 3. 既有实际 Gate 结果

```text
API Runtime Contract: 2 passed
Real HTTP API: 31 passed
Backend regression: 309 passed, 31 deselected
Migration head: 0024_embedding_dimension_contract
Backend Release / Regression Gate: passed
```

以上为此前开发者实际反馈。本次配置化变更未执行前，不将其描述为本轮完整 Gate 证据。

## 4. 当前 Acceptance 结论

当前真实 Provider 指标仍为 Recall@3=0.6、Precision@3=0.333333、Citation correctness=0.333333。它们是冻结 baseline 的实际质量表现，而不是“语义质量已经达到最终产品目标”的证明。

本轮重点是让 evaluation model/provider 与评估参数可自定义，并保证这些配置进入 trace、而不修改既有 baseline。配置化实现完成后必须重新执行本地测试并记录真实结果；不得通过降低阈值或修改 baseline 解决质量问题。

## 5. 本轮完整自动化测试流程

### 5.1 同步最新 main

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform
git fetch origin
git checkout main
git pull --ff-only origin main
git log -3 --oneline
```

应看到远端最新 `175c5cf` 以及本轮配置化提交（若已提交）。

### 5.2 Backend 配置单元测试

```powershell
cd backend
uv run pytest -q tests/unit/test_retrieval_evaluation_config.py tests/unit/test_retrieval_evaluation.py
```

### 5.3 Runtime/API Contract

```powershell
uv run pytest -q tests/api_contract/test_api_runtime_endpoints.py
```

### 5.4 Real Provider 配置化运行

默认读取 `backend/.env` / `.env.local` 中的 provider 配置：

```powershell
uv run python .\scripts\evaluation\knowledge\run_knowledge_retrieval_real_provider.py `
  --k 3 `
  --min-score 0.0 `
  --min-recall-at-k 0.6 `
  --min-precision-at-k 0.333333 `
  --min-mrr 0.6 `
  --min-citation-correctness 0.333333 `
  --max-error-rate 0
```

显式指定 Ollama 模型时：

```powershell
uv run python .\scripts\evaluation\knowledge\run_knowledge_retrieval_real_provider.py `
  --embedding-provider ollama `
  --embedding-base-url http://localhost:11434 `
  --embedding-model nomic-embed-text:latest `
  --embedding-dimension 768 `
  --k 3
```

OpenAI-compatible provider 示例；Secret 只放环境变量：

```powershell
$env:EVAL_EMBEDDING_API_KEY="<local-secret>"
uv run python .\scripts\evaluation\knowledge\run_knowledge_retrieval_real_provider.py `
  --embedding-provider openai-compatible `
  --embedding-base-url http://localhost:8080/v1 `
  --embedding-api-key-env EVAL_EMBEDDING_API_KEY `
  --embedding-model <model-name> `
  --embedding-dimension <dimension> `
  --k 5 `
  --min-score 0.2
Remove-Item Env:EVAL_EMBEDDING_API_KEY
```

如果 Provider / model / dimension / dataset / top-k identity 与冻结 baseline 不一致，不得使用原 baseline 强行通过；应指定独立 `--baseline` 文件或在产品决策后更新 baseline。

### 5.5 Real HTTP API Gate

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

### 5.6 Backend Release / Regression Gate

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

验收要求：只记录实际执行结果；Real runner 返回 0 且 `quality_gate=passed`，Real API Gate 全部通过，Backend regression / migration / Real API 三层 Gate 全部通过，且 trace 中可查询本次 evaluation parameters。

## 6. 下一步

1. 执行本轮配置化单元测试与完整 Backend / Real API Gate。
2. 使用不同模型或参数做一次真实配置验证；identity 改变时不得覆盖原 baseline。
3. 结合真实质量指标与产品目标决定 Phase 2.2 是否关闭。
