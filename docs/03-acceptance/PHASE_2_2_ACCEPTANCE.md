# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**进行中 / 2.2-A Product / Retrieval Quality Contract 设计中**
> 未执行的 Gate 不得标记 Passed。

## 1. Acceptance Scope

验证现有 Knowledge / RAG / Retrieval 链路是否能够通过真实 Embedding Provider、固定评测数据集和可重复指标形成生产质量闭环。

## 2. Acceptance Gates

### A. Product / Retrieval Quality Contract — **设计中**

- [ ] 真实 Embedding Provider Contract 冻结。
- [ ] Evaluation Dataset / Corpus 边界冻结。
- [ ] Dataset version / case schema 冻结。
- [ ] Recall@K 定义冻结。
- [ ] Precision@K 定义冻结。
- [ ] MRR 定义冻结。
- [ ] Citation correctness 定义冻结。
- [ ] latency / provider error rate 观察口径冻结。
- [ ] baseline 与 regression comparison 规则冻结。
- [ ] failure / fallback semantics 冻结。

### B. Evaluation Dataset / Runner

- [ ] Dataset 可版本化。
- [ ] Evaluation runner 可重复执行。
- [ ] 结果包含 Provider / model / dimension / dataset version / retrieval mode。
- [ ] 指标计算自动化。
- [ ] 失败 case 可定位到 case ID。

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

## 3. 2.2-A 当前结论

当前只冻结 Contract、指标、数据集与失败边界。尚未执行 Real Provider Quality Gate，因此不得标记 Phase 2.2 或 2.2-A Passed。

下一步在 Contract 定稿后实现 Dataset / Runner，并以真实 Provider 进行本地质量验证。
