# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**进行中 / 2.2-B 已通过本地 Gate；2.2-C Real Provider Quality Gate 已实现，待真实 Provider 本地执行**
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

本地证据：

```text
Dataset Loader: 4 passed
Retrieval evaluation + Dataset: 10 passed
Backend regression: 279 passed, 30 deselected
Migration head: 0023_organization_membership
Real API: 30 passed
2.2-B runner --k 3: 5/5 cases successful, error_rate=0, recall@3=1.0, precision@3=0.466667, MRR=0.9, quality_gate=passed
```

### C. Real Provider Quality Gate — **实现完成，待本地 Gate**

- [x] 使用真实 Embedding Provider 的 runner 已实现。
- [x] 使用真实 PostgreSQL / pgvector Retrieval 链路。
- [x] Provider failure 保留为 observation / error，不静默 fallback。
- [x] 显式 fallback 字段进入结果；本 Gate 默认 `fallback_used=false`。
- [x] Mock 结果不作为真实质量证据。
- [x] Provider / model / dimension / dataset / retrieval mode / top-k identity 纳入 baseline。
- [x] 首次真实运行支持显式 `--freeze-baseline`；冻结结果不会被标记为 quality Gate Passed。
- [ ] 使用开发者真实 Provider credentials 完成本地 Gate。
- [ ] 冻结真实 Provider baseline。
- [ ] 使用冻结 baseline 重跑并确认 regression Gate。

### D. Regression / Traceability

- [x] Provider / model / dataset identity 可进入 baseline 对比。
- [ ] Citation correctness 有自动化证据。
- [ ] Retrieval Debug / Audit / Observability 可追踪评测结果。

## 3. 2.2-B 当前结论

2.2-B Dataset Loader 与 Runner 已完成，并已在开发者本地执行通过。现有结果只能证明固定 Dataset + PostgreSQL/pgvector + deterministic Mock Embedding 的工程链路，不代表真实模型语义质量。

## 4. 2.2-C 当前结论

Real Provider runner 已直接复用 `OpenAICompatibleEmbeddingProvider`、现有 Dataset Loader、PostgreSQL/pgvector fixture 与 Retrieval Evaluation aggregation。真实 Provider baseline 不预置、不伪造，必须由开发者使用本地未提交 `backend/.env` 完成真实运行后冻结。

下一步：

1. 配置未提交的 `backend/.env`：`EMBEDDING_PROVIDER=openai-compatible`、真实 endpoint、API key、model、dimension；保持 `VECTOR_PROVIDER=pgvector`。
2. 使用 `--freeze-baseline` 执行第一次真实评测并审阅结果。
3. 保留冻结 baseline 后再次执行 runner，确认 regression Gate。
4. 若真实 Provider 结果或错误证据不满足要求，按实际失败记录到 `docs/04-errors/` 后修复。
