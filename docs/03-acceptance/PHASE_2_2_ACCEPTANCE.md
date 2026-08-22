# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**进行中 / 2.2-B Evaluation Dataset / Runner 已实现，尚待本地 Gate**
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

### B. Evaluation Dataset / Runner — **实现完成，待本地 Gate**

- [x] Dataset Loader 对当前 JSONL 执行结构、ID、query、relevant chunk 校验。
- [x] Evaluation runner 可重复执行设计与实现完成。
- [x] 结果包含 dataset schema version、retrieval mode、case detail、latency、error 与聚合指标。
- [x] Recall@K / Precision@K / MRR / error rate / latency 自动化计算接入现有 evaluation service。
- [x] 失败 case 可通过 case detail 定位。
- [ ] 开发者本地 unit / runner Gate 实际执行并记录结果。

### C. Real Provider Quality Gate

- [ ] 使用真实 Embedding Provider。
- [ ] 使用真实 PostgreSQL / pgvector Retrieval 链路。
- [ ] Provider failure 不被隐藏。
- [ ] 显式 fallback 有结果标识。
- [ ] Mock 结果不作为真实质量证据。

### D. Regression / Traceability

- [ ] Provider / model / dataset 变化可进行 baseline 对比。
- [ ] Citation correctness 有自动化证据。
- [ ] Retrieval Debug / Audit / Observability 可追踪评测结果。

## 3. 2.2-B 当前结论

Dataset Loader 与 Runner 已实现并直接复用现有 Retrieval Evaluation / PostgreSQL / pgvector fixture。由于本次实现尚未在开发者本地执行，当前只能记录为“实现完成，待 Gate”，不得标记 Passed。

下一步执行本地 unit / runner Gate；通过后进入 2.2-C Real Provider Quality Gate。
