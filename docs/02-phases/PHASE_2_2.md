# Phase 2.2 — Retrieval Production Quality

> 状态：**正式关闭 / 2.2-B Dataset / Runner、2.2-C Real Provider Quality Gate、2.2-D Retrieval Quality Regression / Traceability 与 2.2-E Model Provider / Model Profile Governance Foundation 均已完成当前定义范围并通过对应 Acceptance Gate。**
> 前置：Phase 2.1 已正式关闭
> 产品主题：企业知识问答的真实语义检索质量、可量化评测与 Provider 回归

Phase 2.2 的目标不是重新建设 Retrieval，而是把现有 Retrieval 能力提升为可重复、可量化、可审计的生产质量体系。

## 2.2-A / B / C / D

2.2-A 已形成真实 Provider、Dataset、Recall@K、Precision@K、MRR、Citation correctness、latency、provider error rate、regression identity 与 failure/fallback 的质量契约。

2.2-B 已完成 Dataset Loader 与 PostgreSQL/pgvector evaluation runner，并有开发者实际执行验证证据。

2.2-C 已完成真实 Ollama Provider + PostgreSQL/pgvector Quality Gate，并冻结真实 baseline。当前 main 的 baseline regression 已通过。

2.2-D 已完成 Provider / model / dimension / dataset / retrieval-mode / top-k identity 与质量指标 regression comparison，以及 Runtime citation / Audit / Observability traceability。

## 2.2-E Model Provider / Model Profile Governance Foundation

E-1 / E-2 完成 Runtime / Evaluation Profile Resolution 与 cross-dimension evaluation governance；E-3 完成 Provider/Profile Frontend Management；E-4 已通过三层实际 Gate 并正式关闭。

### E-4 实际 Acceptance Evidence

```text
Backend Real API Gate:
  32 passed

Frontend Regression Gate:
  18 test files passed
  75 tests passed
  vue-tsc -b passed
  Vite production build passed

Model Provider/Profile Browser E2E:
  2 passed
```

三层 Gate 分工保持独立：Backend Real API 验证真实 HTTP/数据库/权限链路；Frontend Regression 验证 Vitest + production build；Browser E2E 验证真实 Browser → Vue → Backend 用户链路。

### E-4 修复结论

- `448e2f8`：修复 Real API governance test 的 member fixture boundary，确保 member 403 断言使用真实 member membership。
- `be5b9ca`：修复 Element Plus Profile type selector 的 Browser locator，避免 selected-item placeholder pointer interception。
- `bfe6512`：修复 Model Provider/Profile AuditLog organization-scoped 查询。
- `04c23de`：修复 Profile 名称字段 locator strict mode 冲突。
- `92568e2`：清理 AuditLog error-path 单测的预期 console.error 噪声，并显式断言该错误日志。

## Definition of Done

Phase 2.2 已满足：

1. Retrieval Quality Contract 已冻结。
2. Evaluation Dataset 可版本化、可重复执行。
3. Recall@K / Precision@K / MRR / Citation correctness 有自动化计算。
4. Real Provider Quality Gate 通过。
5. Provider / model / dataset regression 可比较。
6. Provider failure / fallback semantics 有自动化证据。
7. Retrieval quality 结果与 Citation / Audit / Observability 可追踪。
8. Evaluation model/provider 与 quality parameters 可显式配置并进入 trace。
9. Model Provider / Model Profile 具备组织范围数据模型、CRUD API、权限、Audit 与 migration。
10. Runtime / Evaluation Profile 接入保留 Provider/Profile/model/dimension identity。
11. Project Status、Phase、Acceptance、错误记录已同步。

**Phase 2.2 正式关闭。**

## 下一阶段边界

下一正式阶段为 Product Roadmap 定义的 **Phase 2.3 Model Provider Governance**。进入 Phase 2.3 前必须先冻结独立 Provider Contract，至少明确：

- Provider routing strategy。
- Fallback eligibility / failure semantics。
- Model whitelist / capability constraints。
- Cost accounting unit and pricing source。
- Usage accounting dimensions and audit identity。

不得通过修改已关闭的 2.2 Retrieval / Profile foundation 来提前实现完整 2.3。
