# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**进行中 / 2.2-B、2.2-C 与当前 2.2-D regression scope 已由开发者本地实际验证；Citation correctness 与 Debug/Audit/Observability traceability 仍未完成**
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

### B. Evaluation Dataset / Runner — **本地 Gate 已通过**

- [x] Dataset Loader 对当前 JSONL 执行结构、ID、query、relevant chunk 校验。
- [x] Evaluation runner 可重复执行设计与实现完成。
- [x] 结果包含 dataset schema version、retrieval mode、case detail、latency、error 与聚合指标。
- [x] Recall@K / Precision@K / MRR / error rate / latency 自动化计算接入现有 evaluation service。
- [x] 失败 case 可通过 case detail 定位。
- [x] 开发者本地 unit / runner Gate 实际执行并记录结果。

本轮实际证据：

```text
Backend regression: 301 passed, 30 deselected
Migration head: 0024_embedding_dimension_contract
Real HTTP API: 30 passed
```

### C. Real Provider Quality Gate — **本地 Gate 已通过**

- [x] 使用真实 Embedding Provider 的 runner 已实现并实际执行。
- [x] 使用真实 PostgreSQL / pgvector Retrieval 链路。
- [x] Provider failure 保留为 observation / error，不静默 fallback。
- [x] 显式 fallback 字段进入结果；本 Gate 实际 `fallback_used=false`、`fallback_count=0`。
- [x] Mock 结果不作为真实质量证据。
- [x] Provider / model / dimension / dataset / retrieval mode / top-k identity 纳入 baseline。
- [x] 首次真实运行使用 `--freeze-baseline` 冻结真实 baseline。
- [x] 使用冻结 baseline 重跑并确认 regression Gate。

本地真实 Provider 证据：

```text
provider=ollama
model=nomic-embed-text:latest
embedding_dimension=768
cases=5
successful_cases=5
error_cases=0
error_rate=0
recall@3=0.6
precision@3=0.333333
mrr=0.6
```

重跑 regression：

```text
baseline.status=checked
identity_changed=false
metric deltas: recall=0, precision=0, mrr=0
provider_error_rate=0
quality_gate=passed
```

### D. Regression / Traceability — **部分完成**

- [x] Provider / model / dataset identity 可进入 baseline 对比。
- [x] Dimension / retrieval mode / top-k identity 可进入 baseline 对比。
- [x] Recall@K / Precision@K / MRR metric delta 可输出 regression report。
- [x] Provider error rate 纳入 regression report。
- [ ] Citation correctness 有自动化证据。
- [ ] Retrieval Debug / Audit / Observability 可追踪评测结果。

## 3. 2.2-C 当前结论

2.2-C Real Provider Quality Gate 已由开发者本地实际完成。Ollama `nomic-embed-text:latest` 返回 768 维 embedding，5/5 evaluation cases 成功写入并从 PostgreSQL/pgvector 检索，error_rate=0、fallback=0。真实 baseline 已冻结并随后成功完成 regression check。

当前 baseline 的 Recall@3=0.6、Precision@3=0.333333、MRR=0.6 是真实、可重复的回归基线，不应被表述为绝对质量达标。当前没有依据在本地人为设置更高绝对门槛，也不得通过修改指标或 fallback 掩盖该结果。

此前 Ollama 503、slow runner startup 与本地环境代理导致的请求失败均已完成分析和修复，相关工程错误已记录。

## 4. 2.2-D 当前结论

Provider / model / dimension / dataset / retrieval mode / top-k 的 regression comparison 已实际通过。下一交付单元为 Citation correctness 以及 Retrieval Debug / Audit / Observability traceability；完成后再进入 Phase 2.2 Acceptance close-out。

## 5. 下一步本地验证

修改 2.2-D Citation / traceability 后必须重新执行至少：

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
uv run python .\scripts\evaluation\knowledge\run_knowledge_retrieval_real_provider.py --k 3
```

真实 Provider / 数据库联调仍必须在开发者本地完成；未实际执行的结果不得写成 Passed。
